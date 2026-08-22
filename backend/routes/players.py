"""
Player-related API endpoints.

Endpoints:
  GET /api/v1/players/{player_id} — player profile and career stats
"""

from fastapi import APIRouter, HTTPException

from models import PlayerProfile

router = APIRouter(prefix="/api/v1/players", tags=["players"])


@router.get("/{player_id}", response_model=PlayerProfile)
async def get_player_profile(player_id: int):
    """
    Returns individual player career stats and match-by-match logs.
    """
    # TODO: Query PostgreSQL by player_id
    raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
