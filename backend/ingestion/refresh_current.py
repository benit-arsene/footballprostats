"""Production entrypoint: refresh current-season Premier League data.

Fetches current-season standings (and fixtures count) from football-data.org,
persists standings idempotently to Neon, and exits with a meaningful status.

Usage:
    cd backend && python -m ingestion.refresh_current
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("refresh_current")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.season import Season  # noqa: E402
from db.models.standing_row import StandingRow  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.models.standing_snapshot import StandingSnapshot  # noqa: E402
from db.models.player import Player  # noqa: E402
from db.models.player_season_stat import PlayerSeasonStat  # noqa: E402
from db.models.match import Match  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.factory import build_provider_registry  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402
from providers.football_data.adapters import FootballDataAdapters  # noqa: E402
from providers.routing import route_provider  # noqa: E402


COMPETITION_ID = 39
SEASON_YEAR = get_season_year()
SEASON_LABEL = f"{SEASON_YEAR}/{SEASON_YEAR + 1}"
SEASON_EXTERNAL_ID = f"PL/{SEASON_YEAR}"
SNAPSHOT_LABEL = f"EPL {SEASON_LABEL} football-data.org standings"


async def _resolve_competition(session):
    result = await session.execute(select(Competition))
    return next((c for c in result.scalars().all() if c.name == "Premier League"), None)


async def _resolve_or_create_season(session, competition):
    repo = Repository(Season)
    existing = await repo.get_by_external_id(
        provider="football_data", external_id=SEASON_EXTERNAL_ID, entity_type="season"
    )
    if existing is not None:
        return existing["season_id"]
    season = Season(
        competition_id=competition.id,
        label=SEASON_LABEL,
        availability_status="imported",
    )
    session.add(season)
    await session.flush()
    sid = season.id
    ext = ExternalId(
        entity_type="season",
        provider="football_data",
        external_id=SEASON_EXTERNAL_ID,
        competition_id=competition.id,
        season_id=sid,
    )
    session.add(ext)
    await session.commit()
    return sid


async def run() -> int:
    registry = build_provider_registry()
    available = set(registry.list_providers())
    if "football_data" not in available:
        logger.error("football_data provider not registered (missing FOOTBALLDATA_KEY)")
        return 1

    name = route_provider("standings", season_label=SEASON_LABEL, data_type="standings",
                          available_providers=available)
    if name != "football_data":
        logger.error("Routing selected %s instead of football_data", name)
        return 1

    provider = registry.get_provider("football_data")

    try:
        async with async_session() as session:
            competition = await _resolve_competition(session)
            if competition is None:
                logger.error("No Premier League competition found")
                return 1
            season_id = await _resolve_or_create_season(session, competition)

        # Fetch standings.
        rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
        logger.info("Fetched %s standings rows from football-data.org", len(rows_raw))

        # Fetch fixtures.
        fixtures_raw = []
        try:
            fixtures_raw = await provider.get_fixtures(league_id=COMPETITION_ID, season=SEASON_YEAR)
            logger.info("Fetched %s fixtures from football-data.org", len(fixtures_raw))
        except Exception as e:
            logger.warning("Fixtures fetch failed (non-fatal): %s", e)

        # Fetch and persist top scorers via API-Football (richer stats).
        ts_created = 0
        ts_reused = 0
        ts_skipped = 0
        try:
            ts_raw = await provider.get_top_scorers(COMPETITION_ID, SEASON_YEAR)
            logger.info("Fetched %s top scorers from football-data.org", len(ts_raw))
        except Exception as e:
            logger.warning("Top scorers fetch failed (non-fatal): %s", e)
            ts_raw = []

        for entry in ts_raw:
            player_info = entry.get("player", {}) or {}
            fd_player_id = str(player_info.get("id"))
            goals = entry.get("goals") or 0
            assists = entry.get("assists") or 0
            # football-data doesn't provide appearances in scorers endpoint
            appearances = 0

            repo_player = Repository(Player)
            existing_player = await repo_player.get_by_external_id(
                provider="football_data", external_id=fd_player_id, entity_type="player"
            )
            if existing_player is None:
                logger.warning("No player mapping for football_data id=%s (%s) — skipping", fd_player_id, player_info.get("name"))
                ts_skipped += 1
                continue
            internal_player_id = existing_player["player_id"]

            async with async_session() as session:
                result = await session.execute(
                    select(PlayerSeasonStat).where(
                        PlayerSeasonStat.player_id == internal_player_id,
                        PlayerSeasonStat.season_id == season_id,
                        PlayerSeasonStat.competition_id == competition.id,
                    )
                )
                existing_stat = result.scalar_one_or_none()
                if existing_stat is not None:
                    if goals and not existing_stat.goals:
                        existing_stat.goals = goals
                    if assists and not existing_stat.assists:
                        existing_stat.assists = assists
                    await session.commit()
                    ts_reused += 1
                    continue
                pss = PlayerSeasonStat(
                    player_id=internal_player_id,
                    season_id=season_id,
                    competition_id=competition.id,
                    goals=goals,
                    assists=assists,
                    appearances=appearances,
                )
                session.add(pss)
                await session.commit()
                ts_created += 1

        logger.info("Top scorers persistence: created=%s reused=%s skipped=%s", ts_created, ts_reused, ts_skipped)
        fx_created = 0
        fx_reused = 0
        fx_skipped = 0
        for api_match in fixtures_raw:
            fd_match_id = str(api_match.get("id"))
            # Already mapped?
            repo_match = Repository(Match) if False else None
            from persistence.repository import Repository as _R
            existing_ext = None
            async with async_session() as session:
                result = await session.execute(
                    select(ExternalId).where(
                        ExternalId.provider == "football_data",
                        ExternalId.entity_type == "match",
                        ExternalId.external_id == fd_match_id,
                    )
                )
                existing_ext = result.scalar_one_or_none()

            if existing_ext is not None:
                fx_reused += 1
                continue

            home_fd = str((api_match.get("homeTeam") or {}).get("id"))
            away_fd = str((api_match.get("awayTeam") or {}).get("id"))
            home_team = await Repository(Team).get_by_external_id(
                provider="football_data", external_id=home_fd, entity_type="team"
            )
            away_team = await Repository(Team).get_by_external_id(
                provider="football_data", external_id=away_fd, entity_type="team"
            )
            if home_team is None or away_team is None:
                fx_skipped += 1
                continue

            home_internal = home_team["team_id"]
            away_internal = away_team["team_id"]

            ms = FootballDataAdapters.match_summary(api_match)
            utc_date = api_match.get("utcDate", "")
            date_str = utc_date[:10] if utc_date else ""
            from datetime import date as _date
            try:
                match_date = _date.fromisoformat(date_str) if date_str else None
            except ValueError:
                match_date = None
            if match_date is None:
                fx_skipped += 1
                continue

            score = api_match.get("score", {}) or {}
            ft = score.get("fullTime", {}) or {}
            status_map = {
                "SCHEDULED": "scheduled", "TIMED": "scheduled",
                "IN_PLAY": "live", "PAUSED": "live",
                "FINISHED": "finished", "POSTPONED": "postponed",
                "SUSPENDED": "postponed", "CANCELLED": "cancelled",
            }
            status = status_map.get(api_match.get("status", "SCHEDULED"), "scheduled")

            async with async_session() as session:
                match = Match(
                    slug=ms.slug,
                    competition_id=COMPETITION_ID_INTERNAL if False else competition.id,
                    season_id=season_id,
                    home_team_id=home_internal,
                    away_team_id=away_internal,
                    date=match_date,
                    kickoff_time=None,
                    status=status,
                    home_score=ft.get("home") or 0,
                    away_score=ft.get("away") or 0,
                )
                session.add(match)
                await session.flush()
                mid = match.id
                ext = ExternalId(
                    entity_type="match",
                    provider="football_data",
                    external_id=fd_match_id,
                    match_id=mid,
                )
                session.add(ext)
                await session.commit()
            fx_created += 1

        logger.info("Fixtures persistence: created=%s reused=%s skipped=%s", fx_created, fx_reused, fx_skipped)

        if not rows_raw:
            logger.warning("No standings rows returned; preserving existing data")
            return 0

        # Persist.
        async with async_session() as session:
            snap_result = await session.execute(
                select(StandingSnapshot).where(
                    StandingSnapshot.season_id == season_id,
                    StandingSnapshot.label == SNAPSHOT_LABEL,
                )
            )
            snapshot = snap_result.scalar_one_or_none()
            created_snapshot = False
            if snapshot is None:
                snapshot = StandingSnapshot(
                    season_id=season_id,
                    matchday=None,
                    label=SNAPSHOT_LABEL,
                    snapshot_date=datetime.now(),
                )
                session.add(snapshot)
                await session.flush()
                created_snapshot = True
            snapshot_id = snapshot.id
            await session.commit()

        created = 0
        reused = 0
        skipped = 0
        for api_row in rows_raw:
            ts = FootballDataAdapters.team_summary(api_row.get("team", {}))
            fd_id = str(ts.id)
            repo = Repository(Team)
            existing_team = await repo.get_by_external_id(
                provider="football_data", external_id=fd_id, entity_type="team"
            )
            if existing_team is None:
                logger.warning("No team mapping for fd_id=%s (%s) — skipping", fd_id, ts.name)
                skipped += 1
                continue
            internal_team_id = existing_team["team_id"]

            async with async_session() as session:
                row_result = await session.execute(
                    select(StandingRow).where(
                        StandingRow.standing_snapshot_id == snapshot_id,
                        StandingRow.team_id == internal_team_id,
                    )
                )
                if row_result.scalar_one_or_none() is not None:
                    reused += 1
                    continue
                sr = FootballDataAdapters.standing_row(api_row)
                row = StandingRow(
                    standing_snapshot_id=snapshot_id,
                    team_id=internal_team_id,
                    position=sr.position,
                    played=sr.played,
                    won=sr.won,
                    drawn=sr.drawn,
                    lost=sr.lost,
                    goals_for=sr.gf,
                    goals_against=sr.ga,
                    goal_difference=sr.gd,
                    points=sr.points,
                    form="".join(sr.form) if isinstance(sr.form, list) else str(sr.form or ""),
                )
                session.add(row)
                await session.commit()
                created += 1

        logger.info("Standings persistence: created=%s reused=%s skipped=%s", created, reused, skipped)

        # If nothing persisted and snapshot was newly created, remove it.
        if created + reused == 0 and created_snapshot:
            async with async_session() as session:
                snap = await session.get(StandingSnapshot, snapshot_id)
                if snap is not None:
                    await session.delete(snap)
                    await session.commit()
            logger.warning("Removed empty snapshot %s", snapshot_id)

        if skipped > 0:
            logger.warning("%s teams skipped (missing mappings)", skipped)

        return 0

    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
