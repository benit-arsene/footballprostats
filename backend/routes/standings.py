"""Standings-related API endpoints (database-backed).

Endpoints:
  GET /api/v1/standings/seasons        — list available seasons for a competition
  GET /api/v1/standings/{season_label} — standings rows for a season from Neon
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from db.models.competition import Competition
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


router = APIRouter(prefix="/api/v1/standings", tags=["standings"])


# In-memory cache for live top scorers (60-minute TTL)
_SCORERS_CACHE = {"data": None, "ts": 0.0}
_SCORERS_TTL = 5400


@router.get("/top-scorers-live")
async def get_live_top_scorers():
    now = time.time()
    if _SCORERS_CACHE["data"] is not None and (now - _SCORERS_CACHE["ts"]) < _SCORERS_TTL:
        return _SCORERS_CACHE["data"]
    try:
        from providers.factory import build_provider_registry

        registry = build_provider_registry()
        available = set(registry.list_providers())
        if "football_data" not in available:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "football-data.org not configured"}})
        provider = registry.get_provider("football_data")
        raw = await provider.get_top_scorers(39, 2026)
        if not raw:
            raise HTTPException(status_code=503, detail={"error": {"code": "UNAVAILABLE", "message": "No scorers available"}})
        rows = []
        for r in raw:
            player = r.get("player", {}) or {}
            team = r.get("team", {}) or {}
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
                "goals": r.get("goals"),
                "assists": r.get("assists"),
                "penalties": r.get("penalties"),
            })
        data = {
            "season": "2026/2027",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "scorers": rows,
        }
        _SCORERS_CACHE["data"] = data
        _SCORERS_CACHE["ts"] = now
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
        rows_raw = await provider.get_standings(39, 2026)
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