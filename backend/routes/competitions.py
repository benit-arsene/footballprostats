"""Competition-related API endpoints (database-backed).

Endpoints:
  GET /api/v1/competitions/{competition_id} — competition hub (standings, top scorers, fixtures)
  GET /api/v1/competitions/{competition_id}/standings — standings table
  GET /api/v1/competitions/{competition_id}/top-scorers — top scorers
  GET /api/v1/competitions/{competition_id}/fixtures — upcoming fixtures
  GET /api/v1/competitions/{competition_id}/results — finished matches

These endpoints are strictly database-first: they read only from PostgreSQL and
never call API-Football, football-data.org, or any other provider. Missing or
stale data is reported explicitly (empty dataset or a structured 404) — no
provider fallback and no ingestion is triggered by a request.

ID handling
-----------
The path parameter is the internal ``competitions.id`` primary key. The public
frontend URLs carry provider competition ids (for example ``epl-39``), so a
provider id is accepted as a fallback and resolved to the internal row through
``external_ids`` (entity_type = "competition"). Internal ids always win. When an
internal id and a provider id of the same value point at different competitions,
the request is rejected as ambiguous (409) instead of silently serving the wrong
competition.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import aliased

from config import get_season_year
from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.match import Match
from db.models.player import Player
from db.models.player_season_stat import PlayerSeasonStat
from db.models.season import Season
from db.models.standing_row import StandingRow as StandingRowModel
from db.models.standing_snapshot import StandingSnapshot
from db.models.team import Team
from db.models.venue import Venue
from db.session import async_session
from models import (
    LeagueProfile,
    LeagueSummary,
    MatchStatus,
    MatchSummary,
    PlayerSummary,
    StandingRow,
    TeamSummary,
    TopScorer,
)

router = APIRouter(prefix="/api/v1/competitions", tags=["competitions"])

# How many rows each dataset supplies, matching the previous provider-backed
# response sizes so the frontend contract does not change.
_HUB_SCORERS_LIMIT = 10
_LIST_SCORERS_LIMIT = 20
_MATCH_LIMIT = 20

_STATUS_BY_VALUE = {status.value: status for status in MatchStatus}


# ─── Errors ──────────────────────────────────────────────────────────────


def _not_found(message: str) -> HTTPException:
    """Structured 404 in the shape the rest of the API returns."""
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "NOT_FOUND", "message": message}},
    )


# ─── ID / season resolution ──────────────────────────────────────────────


def _current_season_label() -> str:
    year = get_season_year()
    return f"{year}/{year + 1}"


async def _resolve_competition(session, competition_id: int) -> Competition:
    """Resolve a path id to a stored competition.

    The internal primary key is authoritative. Only when no internal id is
    matched is the value treated as a provider-side id and resolved through
    ``external_ids`` — this keeps the existing provider-id URLs working without
    ever conflating the two id spaces. If both interpretations match different
    competitions the request is ambiguous, so it is rejected rather than
    answering with the wrong competition.
    """
    internal_result = await session.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    internal = internal_result.scalar_one_or_none()

    ext_result = await session.execute(
        select(ExternalId).where(
            ExternalId.entity_type == "competition",
            ExternalId.external_id == str(competition_id),
        )
    )
    mapped: Competition | None = None
    for ext in ext_result.scalars().all():
        if ext.competition_id is None:
            continue
        mapped_result = await session.execute(
            select(Competition).where(Competition.id == ext.competition_id)
        )
        mapped = mapped_result.scalar_one_or_none()
        if mapped is not None:
            break

    if internal is not None and mapped is not None and internal.id != mapped.id:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "AMBIGUOUS_COMPETITION_ID",
                    "message": (
                        f"Competition id {competition_id} matches internal competition "
                        f"{internal.slug} and provider id of competition {mapped.slug}; "
                        "use the internal competition id"
                    ),
                }
            },
        )

    if internal is not None:
        return internal
    if mapped is not None:
        return mapped

    raise _not_found(f"Competition {competition_id} not found")


async def _resolve_current_season(session, competition_id: int) -> Season | None:
    """Return the stored season that corresponds to the server's current season.

    Returns None when that season has not been registered for the competition;
    callers then report the dataset as unavailable instead of inventing data.
    """
    result = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.label == _current_season_label(),
        )
    )
    return result.scalar_one_or_none()


# ─── Model mapping ───────────────────────────────────────────────────────


def _league_summary(competition: Competition) -> LeagueSummary:
    return LeagueSummary(
        id=competition.id,
        name=competition.name,
        slug=competition.slug,
        country=competition.country or "",
        logo_url=competition.logo_url or "",
    )


def _team_summary(team: Team) -> TeamSummary:
    return TeamSummary(
        id=team.id,
        name=team.name,
        slug=team.slug,
        crest_url=team.crest_url or "",
    )


def _parse_form(form: str | None) -> list[str]:
    """Turn the stored form string into the last-five result list the UI expects.

    Managers store form either as a compact string ("WWDLW") or a
    comma-separated list ("W,D,L,W,W"); both shapes are accepted.
    """
    if not form:
        return []
    text = str(form)
    parts = [part.strip() for part in text.split(",")] if "," in text else list(text.strip())
    return [part for part in parts if part][-5:]


def _match_summary(
    match: Match,
    home_team: Team,
    away_team: Team,
    venue: Venue | None,
    competition: Competition,
) -> MatchSummary:
    status = _STATUS_BY_VALUE.get(match.status, MatchStatus.SCHEDULED)
    return MatchSummary(
        id=match.id,
        slug=match.slug,
        status=status,
        minute=match.minute,
        date=match.date.isoformat() if match.date else "",
        kickoff_time=match.kickoff_time.strftime("%H:%M") if match.kickoff_time else "",
        venue=venue.name if venue is not None else "",
        league=_league_summary(competition),
        home_team=_team_summary(home_team),
        away_team=_team_summary(away_team),
        home_score=match.home_score or 0,
        away_score=match.away_score or 0,
    )


# ─── Dataset queries ─────────────────────────────────────────────────────


async def _standings(session, season: Season | None) -> list[StandingRow]:
    """Rows of the latest stored snapshot that actually has rows.

    Snapshots are ordered newest first; the first snapshot that contributes
    rows in that ordering is the "latest valid" one. Empty snapshots (for
    example a failed refresh) are skipped rather than shown as an empty table.
    """
    if season is None:
        return []

    result = await session.execute(
        select(StandingRowModel, Team, StandingSnapshot)
        .join(Team, StandingRowModel.team_id == Team.id)
        .join(
            StandingSnapshot,
            StandingRowModel.standing_snapshot_id == StandingSnapshot.id,
        )
        .where(StandingSnapshot.season_id == season.id)
        .order_by(
            StandingSnapshot.snapshot_date.desc().nullslast(),
            StandingSnapshot.id.desc(),
            StandingRowModel.position.asc(),
        )
    )

    grouped: dict[int, list[tuple[StandingRowModel, Team]]] = {}
    for row, team, snapshot in result.all():
        grouped.setdefault(snapshot.id, []).append((row, team))

    if not grouped:
        return []

    latest = next(iter(grouped.values()))
    return [
        StandingRow(
            position=row.position,
            team=_team_summary(team),
            played=row.played,
            won=row.won,
            drawn=row.drawn,
            lost=row.lost,
            gf=row.goals_for,
            ga=row.goals_against,
            gd=row.goal_difference,
            points=row.points,
            form=_parse_form(row.form),
        )
        for row, team in latest
    ]


async def _top_scorers(
    session, season: Season | None, limit: int
) -> list[TopScorer]:
    """Top scorers for a season from ``player_season_stats``.

    The competition is implied by the season (``seasons.competition_id``), so
    the stats row itself needs no competition column. A player can hold one
    stats row per team in a season; only their best-scoring row is kept so a
    scorer is never listed twice.
    """
    if season is None:
        return []

    result = await session.execute(
        select(PlayerSeasonStat, Player, Team)
        .join(Player, PlayerSeasonStat.player_id == Player.id)
        .join(Team, PlayerSeasonStat.team_id == Team.id)
        .where(PlayerSeasonStat.season_id == season.id)
        .order_by(
            PlayerSeasonStat.goals.desc(),
            PlayerSeasonStat.assists.desc(),
            Player.name.asc(),
        )
        .limit(limit)
    )

    scorers: list[TopScorer] = []
    seen_players: set[int] = set()
    for stat, player, team in result.all():
        if player.id in seen_players:
            continue
        seen_players.add(player.id)
        scorers.append(
            TopScorer(
                player=PlayerSummary(
                    id=player.id,
                    name=player.name,
                    slug=player.slug,
                    position=player.position or "",
                    number=player.number,
                    nationality=player.nationality or "",
                ),
                team=_team_summary(team),
                goals=stat.goals or 0,
                assists=stat.assists or 0,
            )
        )
    return scorers


async def _upcoming_fixtures(
    session, competition: Competition, season: Season | None
) -> list[MatchSummary]:
    """Scheduled matches from today onwards for the stored season."""
    if season is None:
        return []

    home = aliased(Team)
    away = aliased(Team)
    result = await session.execute(
        select(Match, home, away, Venue)
        .join(home, Match.home_team_id == home.id)
        .join(away, Match.away_team_id == away.id)
        .outerjoin(Venue, Match.venue_id == Venue.id)
        .where(
            Match.competition_id == competition.id,
            Match.season_id == season.id,
            Match.status == MatchStatus.SCHEDULED.value,
            Match.date >= date.today(),
        )
        .order_by(
            Match.date.asc(),
            Match.kickoff_time.asc().nullslast(),
            Match.id.asc(),
        )
        .limit(_MATCH_LIMIT)
    )

    return [
        _match_summary(match, home_team, away_team, venue, competition)
        for match, home_team, away_team, venue in result.all()
    ]


async def _results(
    session, competition: Competition, season: Season | None
) -> list[MatchSummary]:
    """Most recent finished matches for the stored season."""
    if season is None:
        return []

    home = aliased(Team)
    away = aliased(Team)
    result = await session.execute(
        select(Match, home, away, Venue)
        .join(home, Match.home_team_id == home.id)
        .join(away, Match.away_team_id == away.id)
        .outerjoin(Venue, Match.venue_id == Venue.id)
        .where(
            Match.competition_id == competition.id,
            Match.season_id == season.id,
            Match.status == MatchStatus.FINISHED.value,
        )
        .order_by(
            Match.date.desc(),
            Match.kickoff_time.desc().nullslast(),
            Match.id.desc(),
        )
        .limit(_MATCH_LIMIT)
    )

    return [
        _match_summary(match, home_team, away_team, venue, competition)
        for match, home_team, away_team, venue in result.all()
    ]


# ─── Routes ──────────────────────────────────────────────────────────────


@router.get("/{competition_id}", response_model=LeagueProfile)
async def get_competition_profile(competition_id: int):
    """Returns competition hub data: standings, top scorers, fixtures."""
    async with async_session() as session:
        competition = await _resolve_competition(session, competition_id)
        season = await _resolve_current_season(session, competition.id)

        standings = await _standings(session, season)
        top_scorers = await _top_scorers(session, season, _HUB_SCORERS_LIMIT)
        fixtures = await _upcoming_fixtures(session, competition, season)

    return LeagueProfile(
        **_league_summary(competition).model_dump(),
        # Falls back to the server's current season label when no season row
        # exists, preserving the response contract; the datasets are empty.
        season=season.label if season is not None else _current_season_label(),
        standings=standings,
        top_scorers=top_scorers,
        fixtures=fixtures,
    )


@router.get("/{competition_id}/standings")
async def get_competition_standings(competition_id: int):
    """Returns the standings table for a competition's current season."""
    async with async_session() as session:
        competition = await _resolve_competition(session, competition_id)
        season = await _resolve_current_season(session, competition.id)
        return await _standings(session, season)


@router.get("/{competition_id}/top-scorers")
async def get_competition_top_scorers(competition_id: int):
    """Returns the top scorers for a competition's current season."""
    async with async_session() as session:
        competition = await _resolve_competition(session, competition_id)
        season = await _resolve_current_season(session, competition.id)
        return await _top_scorers(session, season, _LIST_SCORERS_LIMIT)


@router.get("/{competition_id}/fixtures")
async def get_competition_fixtures(competition_id: int):
    """Returns upcoming fixtures for a competition's current season."""
    async with async_session() as session:
        competition = await _resolve_competition(session, competition_id)
        season = await _resolve_current_season(session, competition.id)
        return await _upcoming_fixtures(session, competition, season)


@router.get("/{competition_id}/results")
async def get_competition_results(competition_id: int):
    """Returns finished matches (results) for a competition's current season."""
    async with async_session() as session:
        competition = await _resolve_competition(session, competition_id)
        season = await _resolve_current_season(session, competition.id)
        return await _results(session, competition, season)
