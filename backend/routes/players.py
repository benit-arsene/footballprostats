"""Player-related API endpoints."""

import re

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from config import get_season_year
from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.player import Player
from db.models.player_season_stat import PlayerSeasonStat
from db.models.season import Season
from db.models.team import Team
from db.session import async_session
from persistence.repository import Repository

router = APIRouter(prefix="/api/v1/players", tags=["players"])

_PLAYER_PROVIDERS = ("football_data", "api_football")


async def _resolve_player(identifier: str) -> Player:
    players = Repository(Player)
    player = await players.get_by_slug(identifier)
    if player is not None:
        return player

    suffix = re.fullmatch(r"(?:(.+)-)?(\d+)", identifier)
    if suffix is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Player not found"}},
        )

    slug_part, raw_id = suffix.groups()
    external_id = raw_id

    if slug_part:
        canonical_id = int(raw_id)
        canonical_player = await players.get_by_id(canonical_id)
        if canonical_player is not None and canonical_player.slug == slug_part:
            return canonical_player

    async with async_session() as session:
        result = await session.execute(
            select(ExternalId.player_id).where(
                ExternalId.entity_type == "player",
                ExternalId.provider.in_(_PLAYER_PROVIDERS),
                ExternalId.external_id == external_id,
                ExternalId.player_id.is_not(None),
            )
        )
        canonical_ids = set(result.scalars().all())

    if len(canonical_ids) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "AMBIGUOUS_MAPPING",
                    "message": "Player ID is ambiguous across provider mappings",
                }
            },
        )
    if not canonical_ids:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Player not found"}},
        )

    player = await players.get_by_id(canonical_ids.pop())
    if player is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Player not found"}},
        )
    return player


async def _current_season_rows(player_id: int) -> list[tuple]:
    async with async_session() as session:
        result = await session.execute(
            select(PlayerSeasonStat, Season, Team, Competition)
            .join(Season, PlayerSeasonStat.season_id == Season.id)
            .join(Team, PlayerSeasonStat.team_id == Team.id)
            .join(Competition, Season.competition_id == Competition.id)
            .where(PlayerSeasonStat.player_id == player_id)
            .order_by(Season.label.desc(), PlayerSeasonStat.id.desc())
        )
        return list(result.all())


async def _live_scorer(player: Player, competition_id: int) -> tuple[dict | None, str | None]:
    from routes.standings import get_live_top_scorers

    payload = await get_live_top_scorers(competition_id)
    scorers = payload.get("scorers", [])
    async with async_session() as session:
        result = await session.execute(
            select(ExternalId.external_id).where(
                ExternalId.entity_type == "player",
                ExternalId.provider == "football_data",
                ExternalId.player_id == player.id,
            )
        )
        player_external_ids = set(result.scalars().all())

        for scorer in scorers:
            scorer_player_id = scorer.get("player", {}).get("id")
            if scorer_player_id is None or str(scorer_player_id) not in player_external_ids:
                continue
            mapped = await session.execute(
                select(ExternalId.player_id).where(
                    ExternalId.entity_type == "player",
                    ExternalId.provider == "football_data",
                    ExternalId.external_id == str(scorer_player_id),
                    ExternalId.player_id.is_not(None),
                )
            )
            mapped_player_ids = set(mapped.scalars().all())
            if mapped_player_ids != {player.id}:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": {
                            "code": "AMBIGUOUS_MAPPING",
                            "message": "Live scorer ID has an ambiguous player mapping",
                        }
                    },
                )
            return scorer, payload.get("season")
    return None, payload.get("season")


async def _team_summary(
    scorer: dict | None,
    season_rows: list[tuple],
) -> dict:
    if scorer is not None:
        scorer_team = scorer.get("team", {})
        scorer_team_id = scorer_team.get("id")
        if scorer_team_id is not None:
            team_mapping = await Repository(Team).get_by_external_id(
                provider="football_data",
                external_id=str(scorer_team_id),
                entity_type="team",
            )
            if team_mapping is not None:
                team = await Repository(Team).get_by_id(team_mapping["team_id"])
                if team is not None:
                    return {
                        "id": team.id,
                        "name": team.name,
                        "slug": team.slug,
                        "crest_url": team.crest_url or "",
                    }
        if scorer_team.get("name"):
            return {
                "id": 0,
                "name": scorer_team["name"],
                "slug": "",
                "crest_url": scorer_team.get("crest_url") or "",
            }

    if season_rows:
        team = season_rows[0][2]
        return {
            "id": team.id,
            "name": team.name,
            "slug": team.slug,
            "crest_url": team.crest_url or "",
        }
    return {"id": 0, "name": "", "slug": "", "crest_url": ""}


@router.get("/{player_id}")
async def get_player_profile(player_id: str):
    """Return stored player identity and verified, season-scoped statistics."""
    player = await _resolve_player(player_id)
    season_rows = await _current_season_rows(player.id)
    season_year = get_season_year()
    current_season_label = f"{season_year}/{season_year + 1}"
    current_row = next(
        (row for row in season_rows if row[1].label == current_season_label),
        None,
    )

    scorer = None
    scorer_season = None
    if current_row is not None:
        scorer, scorer_season = await _live_scorer(player, current_row[3].id)

    profile_seasons = []
    if scorer is not None:
        scorer_player = scorer.get("player", {})
        stats = {"season": scorer_season or current_season_label}
        if current_row is not None:
            stats["competition_name"] = current_row[3].name
        for field, value in (
            ("appearances", scorer.get("played_matches")),
            ("goals", scorer.get("goals")),
            ("assists", 0 if scorer.get("assists") is None else scorer.get("assists")),
        ):
            if isinstance(value, int):
                stats[field] = value
        profile_seasons.append(stats)
    else:
        scorer_player = {}

    team = await _team_summary(scorer, season_rows)
    stored_position = player.position if player.position != "Unknown" else ""
    return {
        "id": player.id,
        "name": scorer_player.get("name") or player.name,
        "slug": player.slug,
        "position": stored_position
        or scorer_player.get("position")
        or "",
        "number": player.number
        if player.number is not None
        else scorer_player.get("shirt_number"),
        "nationality": player.nationality or scorer_player.get("nationality") or "",
        "date_of_birth": player.date_of_birth
        or scorer_player.get("date_of_birth")
        or "",
        "height_cm": player.height_cm,
        "foot": player.foot or "",
        "team": team,
        "season_stats": profile_seasons,
        "match_logs": [],
    }
