"""
Team-related API endpoints.

Endpoints:
  GET /api/v1/teams/{team_id} — team profile with squad and records
"""

from fastapi import APIRouter, HTTPException

from models import TeamProfile
from services import football_api
from services.mapper import map_team_summary, map_player_summary, map_league_summary, make_slug
from config import get_season_year

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.get("/{team_id}", response_model=TeamProfile)
async def get_team_profile(team_id: int):
    """
    Returns full team profile including bio, current squad list.
    """
    try:
        team_data = await football_api.get_team(team_id)
        if not team_data:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"Team {team_id} not found"}},
            )

        team_info = team_data.get("team", {})
        venue = team_data.get("venue", {})
        league = team_info.get("league", {})

        # Get squad
        season = get_season_year()
        try:
            players_data = await football_api.get_team_players(team_id, season)
            squad = []
            for p in players_data:
                player = p.get("player", {})
                squad.append(map_player_summary(player))
        except Exception:
            squad = []

        # Build league summary
        league_summary = map_league_summary(league) if league.get("id") else None
        if not league_summary:
            from models import LeagueSummary
            league_summary = LeagueSummary(
                id=0, name="Unknown", slug="unknown-0", country="", logo_url=""
            )

        return TeamProfile(
            id=team_info["id"],
            name=team_info.get("name", ""),
            slug=make_slug(team_info.get("name", ""), team_info["id"]),
            short_name=team_info.get("name", "")[:3].upper(),
            crest_url=team_info.get("logo", ""),
            league=league_summary,
            founded=team_info.get("founded", 0),
            venue=venue.get("name", ""),
            coach="",  # Not always available
            squad=squad,
        )
    except HTTPException:
        raise
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})
