"""Standings-related API endpoints (database-backed).

Endpoints:
  GET /api/v1/standings/seasons          — list available seasons for a competition
  GET /api/v1/standings/{season_id}      — standings rows for a season from Neon
  GET /api/v1/standings/top-scorers-live — live top scorers for a competition
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from config import get_season_year

from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.season import Season
from db.models.standing_row import StandingRow
from db.models.standing_snapshot import StandingSnapshot
from db.models.team import Team
from db.session import async_session
from sqlalchemy import select

import time

# In-memory cache for live standings (10-minute TTL)
_LIVE_CACHE = {"data": None, "ts": 0.0}
_LIVE_TTL = 600

# In-memory cache for live top scorers (90-minute TTL), keyed by the
# football-data.org competition id so the same competition is cached once
# regardless of how the caller referenced it.
_SCORERS_CACHE: dict[int, dict] = {}
_SCORERS_TTL = 5400


router = APIRouter(prefix="/api/v1/standings", tags=["standings"])


def _scorers_season_label(payload: dict) -> str | None:
    """Season label derived from the provider payload.

    Uses the season start/end years published by football-data.org and falls
    back to the requested season filter. Never hardcodes a season.
    """
    season = payload.get("season") or {}
    start = str(season.get("startDate") or "")
    end = str(season.get("endDate") or "")
    if len(start) >= 4 and len(end) >= 4:
        return f"{start[:4]}/{end[:4]}"

    filters = payload.get("filters") or {}
    try:
        start_year = int(filters.get("season"))
    except (TypeError, ValueError):
        return None
    return f"{start_year}/{start_year + 1}"


@router.get("/competition-by-slug/{slug}")
async def get_competition_by_slug(slug: str):
    async with async_session() as session:
        result = await session.execute(select(Competition).where(Competition.slug == slug))
        competition = result.scalar_one_or_none()
    if competition is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Competition not found: {slug}"}})
    return {"id": competition.id, "name": competition.name, "slug": competition.slug}


def _football_data_competition_id(ext: ExternalId) -> int | None:
    """Map an external-id row to a football-data.org competition id."""
    from providers.football_data.adapters import CODE_TO_COMPETITION_ID, COMPETITION_CODE_MAP

    if ext.provider == "football_data":
        return CODE_TO_COMPETITION_ID.get(ext.external_id)
    # api_football and football-data.org share the same numeric competition ids.
    try:
        value = int(ext.external_id)
    except (TypeError, ValueError):
        return None
    return value if value in COMPETITION_CODE_MAP else None


async def _resolve_scorers_competition_id(competition_id: int) -> int:
    """Resolve a competition reference to a football-data.org competition id.

    The canonical reference is the internal competition id used across the
    standings API (Premier League = 1, La Liga = 2). A provider-side
    competition id (39 for the Premier League, 140 for La Liga) is accepted
    as well so callers that already track provider ids keep working.
    """
    from providers.football_data.adapters import COMPETITION_CODE_MAP

    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.entity_type == "competition",
                ExternalId.competition_id == competition_id,
            )
        )
        rows = list(result.scalars().all())

        if not rows:
            result = await session.execute(
                select(ExternalId).where(
                    ExternalId.entity_type == "competition",
                    ExternalId.external_id == str(competition_id),
                )
            )
            rows = list(result.scalars().all())

        if not rows:
            code = COMPETITION_CODE_MAP.get(competition_id)
            if code is not None:
                result = await session.execute(
                    select(ExternalId).where(
                        ExternalId.entity_type == "competition",
                        ExternalId.provider == "football_data",
                        ExternalId.external_id == code,
                    )
                )
                rows = list(result.scalars().all())

    if not rows:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Competition mapping not found"}})

    rows.sort(key=lambda r: 0 if r.provider == "football_data" else 1)
    for ext in rows:
        resolved = _football_data_competition_id(ext)
        if resolved is not None:
            return resolved

    raise HTTPException(status_code=400, detail={"error": {"code": "UNSUPPORTED_COMPETITION", "message": f"Unsupported competition id: {competition_id}"}})


async def _scorers_competition_name(provider_competition_id: int) -> str | None:
    """Display name of the competition a scorers payload belongs to.

    Used as a fallback when the provider omits the competition block. The name
    comes from the `competitions` row so it always matches the rows that were
    rendered next to it.
    """
    from providers.football_data.adapters import COMPETITION_CODE_MAP

    candidates = {str(provider_competition_id)}
    code = COMPETITION_CODE_MAP.get(provider_competition_id)
    if code is not None:
        candidates.add(code)

    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.entity_type == "competition",
                ExternalId.external_id.in_(candidates),
            )
        )
        rows = list(result.scalars().all())

    for ext in rows:
        if ext.competition_id is None:
            continue
        async with async_session() as session:
            result = await session.execute(
                select(Competition).where(Competition.id == ext.competition_id)
            )
            competition = result.scalar_one_or_none()
        if competition is not None and competition.name:
            return competition.name
    return None


@router.get("/top-scorers-live")
async def get_live_top_scorers(competition_id: int):
    """Live top scorers for a competition.

    `competition_id` is the internal competition id; provider-side competition
    ids are accepted as a fallback.
    """
    provider_competition_id = await _resolve_scorers_competition_id(competition_id)

    now = time.time()
    cached = _SCORERS_CACHE.get(provider_competition_id)
    if cached is not None and (now - cached["ts"]) < _SCORERS_TTL:
        return cached["data"]
    try:
        from providers.factory import build_provider_registry

        registry = build_provider_registry()
        available = set(registry.list_providers())
        if "football_data" not in available:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "football-data.org not configured"}})
        provider = registry.get_provider("football_data")
        payload = await provider.get_top_scorers_payload(provider_competition_id, get_season_year())
        raw = payload.get("scorers", [])
        if not raw:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "No scorers available"}})
        rows = []
        goals_total = 0
        for r in raw:
            player = r.get("player", {}) or {}
            team = r.get("team", {}) or {}
            goals = r.get("goals")
            if isinstance(goals, int):
                goals_total += goals
            rows.append({
                "player": {
                    "name": player.get("name", ""),
                    "id": player.get("id"),
                    "position": player.get("position"),
                    "section": player.get("section"),
                    "nationality": player.get("nationality"),
                    "shirt_number": player.get("shirtNumber"),
                    "date_of_birth": player.get("dateOfBirth"),
                },
                "team": {
                    "name": team.get("name", ""),
                    "id": team.get("id"),
                    "short_name": team.get("shortName"),
                    "tla": team.get("tla"),
                    "crest_url": team.get("crest"),
                },
                "played_matches": r.get("playedMatches"),
                "goals": goals,
                "assists": r.get("assists"),
                "penalties": r.get("penalties"),
            })
        provider_season = payload.get("season") or {}
        provider_competition = payload.get("competition") or {}
        competition_name = provider_competition.get("name")
        if not competition_name:
            try:
                competition_name = await _scorers_competition_name(provider_competition_id)
            except Exception:
                competition_name = None
        data = {
            "season": _scorers_season_label(payload),
            "competition_name": competition_name,
            "current_matchday": provider_season.get("currentMatchday"),
            "scorers_count": payload.get("count") or len(rows),
            "goals_total": goals_total,
            "scorers": rows,
        }
        _SCORERS_CACHE[provider_competition_id] = {"data": data, "ts": now}
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/live")
async def get_live_standings():
    now = time.time()
    if _LIVE_CACHE["data"] is not None and (now - _LIVE_CACHE["ts"]) < _LIVE_TTL:
        return _LIVE_CACHE["data"]
    try:
        from providers.factory import build_provider_registry
        from providers.routing import route_provider

        registry = build_provider_registry()
        available = set(registry.list_providers())
        if "football_data" not in available:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "football-data.org not configured"}})
        provider = registry.get_provider("football_data")
        rows_raw = await provider.get_standings(39, get_season_year())
        if not rows_raw:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "No standings available"}})
        data = {
            "season": "2026/2027",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "rows": [
                {
                    "position": r.get("position", i + 1),
                    "team": {"id": r.get("team", {}).get("id"), "name": r.get("team", {}).get("name"), "slug": "", "crest_url": r.get("team", {}).get("crest", "")},
                    "played": r.get("playedGames", 0),
                    "won": r.get("won", 0),
                    "drawn": r.get("draw", 0),
                    "lost": r.get("lost", 0),
                    "goals_for": r.get("goalsFor", 0),
                    "goals_against": r.get("goalsAgainst", 0),
                    "goal_difference": r.get("goalDifference", 0),
                    "gd": r.get("goalDifference", 0),
                    "points": r.get("points", 0),
                    "form": r.get("form", ""),
                }
                for i, r in enumerate(rows_raw)
            ],
        }
        _LIVE_CACHE["data"] = data
        _LIVE_CACHE["ts"] = now
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/seasons")
async def list_seasons(competition_id: int = 1):
    """Return the list of seasons available in the database for a competition."""
    async with async_session() as session:
        result = await session.execute(
            select(Season).where(Season.competition_id == competition_id).order_by(Season.label)
        )
        seasons = result.scalars().all()
        return [{"id": s.id, "label": s.label} for s in seasons]


@router.get("/label/{season_label:path}")
async def get_standings_by_label(season_label: str):
    """Return standings for a season identified by its label (e.g. '2023/2024')."""
    async with async_session() as session:
        result = await session.execute(
            select(Season).where(Season.label == season_label)
        )
        season = result.scalar_one_or_none()
        if season is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"Season {season_label} not found"}},
            )

        snap_result = await session.execute(
            select(StandingSnapshot)
            .where(StandingSnapshot.season_id == season.id)
            .order_by(StandingSnapshot.id.desc())
        )
        snapshot = snap_result.scalars().first()
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"No standings for season {season_label}"}},
            )

        rows_result = await session.execute(
            select(StandingRow, Team)
            .join(Team, StandingRow.team_id == Team.id)
            .where(StandingRow.standing_snapshot_id == snapshot.id)
            .order_by(StandingRow.position)
        )
        rows = rows_result.all()

        return {
            "season": season.label,
            "snapshot_id": snapshot.id,
            "label": snapshot.label,
            "rows": [
                {
                    "position": r.position,
                    "team": {"id": t.id, "name": t.name, "slug": t.slug, "crest_url": t.crest_url},
                    "played": r.played,
                    "won": r.won,
                    "drawn": r.drawn,
                    "lost": r.lost,
                    "goals_for": r.goals_for,
                    "goals_against": r.goals_against,
                    "goal_difference": r.goal_difference,
                    "gd": r.goal_difference,
                    "points": r.points,
                    "form": r.form,
                }
                for r, t in rows
            ],
        }


@router.get("/{season_id}")
async def get_standings_by_season(season_id: int):
    """Return the standings table for a season (by internal season ID) from Neon."""
    async with async_session() as session:
        season = await session.get(Season, season_id)
        if season is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"Season {season_id} not found"}},
            )

        snap_result = await session.execute(
            select(StandingSnapshot)
            .where(StandingSnapshot.season_id == season.id)
            .order_by(StandingSnapshot.id.desc())
        )
        snapshot = snap_result.scalars().first()
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"No standings for season {season.label}"}},
            )

        rows_result = await session.execute(
            select(StandingRow, Team)
            .join(Team, StandingRow.team_id == Team.id)
            .where(StandingRow.standing_snapshot_id == snapshot.id)
            .order_by(StandingRow.position)
        )
        rows = rows_result.all()

        return {
            "season": season.label,
            "snapshot_id": snapshot.id,
            "label": snapshot.label,
            "rows": [
                {
                    "position": r.position,
                    "team": {"id": t.id, "name": t.name, "slug": t.slug, "crest_url": t.crest_url},
                    "played": r.played,
                    "won": r.won,
                    "drawn": r.drawn,
                    "lost": r.lost,
                    "goals_for": r.goals_for,
                    "goals_against": r.goals_against,
                    "goal_difference": r.goal_difference,
                    "gd": r.goal_difference,
                    "points": r.points,
                    "form": r.form,
                }
                for r, t in rows
            ],
        }