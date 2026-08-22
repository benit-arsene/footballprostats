"""
Team-related API endpoints.

Endpoints:
  GET /api/v1/teams/{team_id} — team profile with squad and records
"""

from fastapi import APIRouter, HTTPException

from models import TeamProfile

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.get("/{team_id}", response_model=TeamProfile)
async def get_team_profile(team_id: int):
    """
    Returns full team profile including bio, current squad list,
    and head-to-head records.
    """
    # TODO: Query PostgreSQL by team_id
    raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
