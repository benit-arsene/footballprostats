"""
League-related API endpoints.

Endpoints:
  GET /api/v1/leagues/{league_id} — competition hub with standings and fixtures
"""

from fastapi import APIRouter, HTTPException

from models import LeagueProfile
from services import football_api
from services.mapper import map_standing_row, map_top_scorer, map_match_summary
from services.football_api import get_season_year

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])


@router.get("/{league_id}", response_model=LeagueProfile)
async def get_league_profile(league_id: int):
    """
    Returns competition hub data: standings table, top scorers,
    and full season calendar.
    """
    try:
        season = get_season_year()

        # Get league info
        league_data = await football_api.get_league(league_id, season)
        if not league_data:
            raise HTTPException(status_code=404, detail=f"League {league_id} not found")

        league_info = league_data.get("league", {})
        country = league_data.get("country", {})

        # Get standings
        try:
            standings_data = await football_api.get_standings(league_id, season)
            standings = [map_standing_row(row) for row in standings_data]
        except Exception:
            standings = []

        # Get top scorers
        try:
            scorers_data = await football_api.get_top_scorers(league_id, season)
            top_scorers = [map_top_scorer(p) for p in scorers_data[:10]]
        except Exception:
            top_scorers = []

        # Get fixtures
        try:
            from datetime import date
            today = date.today().isoformat()
            fixtures_data = await football_api.get_fixtures_by_date(today, league_id)
            fixtures = [map_match_summary(f) for f in fixtures_data[:20]]
        except Exception:
            fixtures = []

        from models import LeagueSummary
        league_summary = LeagueSummary(
            id=league_info.get("id", league_id),
            name=league_info.get("name", f"League {league_id}"),
            slug=f"{league_info.get('name', f'league-{league_id}').lower().replace(' ', '-')}-{league_id}",
            country=country.get("name", ""),
            logo_url=league_info.get("logo", ""),
        )

        return LeagueProfile(
            **league_summary.model_dump(),
            season=f"{season}/{season + 1}",
            standings=standings,
            top_scorers=top_scorers,
            fixtures=fixtures,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")
