"""
League-related API endpoints.

Endpoints:
  GET /api/v1/leagues/{league_id} — competition hub with standings and fixtures
"""

from fastapi import APIRouter, HTTPException

from models import LeagueProfile

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])


@router.get("/{league_id}", response_model=LeagueProfile)
async def get_league_profile(league_id: int):
    """
    Returns competition hub data: standings table, top scorers,
    and full season calendar.
    """
    # TODO: Query PostgreSQL by league_id
    raise HTTPException(status_code=404, detail=f"League {league_id} not found")
