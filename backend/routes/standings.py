"""Standings-related API endpoints (database-backed).

Endpoints:
  GET /api/v1/standings/seasons        — list available seasons for a competition
  GET /api/v1/standings/{season_label} — standings rows for a season from Neon
"""

from fastapi import APIRouter, HTTPException

from db.models.competition import Competition
from db.models.season import Season
from db.models.standing_row import StandingRow
from db.models.standing_snapshot import StandingSnapshot
from db.models.team import Team
from db.session import async_session
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/standings", tags=["standings"])


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