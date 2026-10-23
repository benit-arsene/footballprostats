"""
Competition-related API endpoints.

Endpoints:
  GET /api/v1/competitions/{competition_id} — competition hub (standings, top scorers, fixtures)
  GET /api/v1/competitions/{competition_id}/standings — standings table
  GET /api/v1/competitions/{competition_id}/top-scorers — top scorers
  GET /api/v1/competitions/{competition_id}/fixtures — upcoming fixtures
  GET /api/v1/competitions/{competition_id}/results — finished matches
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from providers.factory import build_provider_registry

from models import LeagueProfile, LeagueSummary, StandingRow, TopScorer, MatchSummary
from services import football_api
from services.mapper import map_standing_row, map_top_scorer, map_match_summary, make_slug
from config import get_season_year

router = APIRouter(prefix="/api/v1/competitions", tags=["competitions"])

_registry = build_provider_registry()


async def _get_top_scorers(competition_id: int, season: int):
    """Get top scorers using football-data.org when available (same as /standings/top-scorers-live)."""
    available = set(_registry.list_providers())
    if "football_data" in available:
        provider = _registry.get_provider("football_data")
        payload = await provider.get_top_scorers_payload(competition_id, season)
        return payload.get("scorers", [])
    # Fall back to api_football
    return await football_api.get_top_scorers(competition_id, season)


async def _build_league_profile(competition_id: int) -> LeagueProfile:
    season = get_season_year()

    league_data = await football_api.get_league(competition_id, season)
    if not league_data:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Competition {competition_id} not found"}},
        )

    league_info = league_data.get("league", {})
    country = league_data.get("country", {})

    standings_data = await football_api.get_standings(competition_id, season)
    standings = [map_standing_row(row) for row in standings_data]

    scorers_data = await _get_top_scorers(competition_id, season)
    top_scorers = [map_top_scorer(p) for p in scorers_data[:10]]

    today = date.today().isoformat()
    fixtures_data = await football_api.get_fixtures_by_date(today, competition_id, season=season)
    fixtures = [map_match_summary(f) for f in fixtures_data[:20]]

    league_summary = LeagueSummary(
        id=league_info.get("id", competition_id),
        name=league_info.get("name", f"Competition {competition_id}"),
        slug=make_slug(league_info.get("name", f"competition-{competition_id}"), competition_id),
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


@router.get("/{competition_id}", response_model=LeagueProfile)
async def get_competition_profile(competition_id: int):
    """Returns competition hub data: standings, top scorers, fixtures."""
    return await _build_league_profile(competition_id)


@router.get("/{competition_id}/standings")
async def get_competition_standings(competition_id: int):
    """Returns the standings table for a competition's current season."""
    season = get_season_year()
    try:
        standings_data = await football_api.get_standings(competition_id, season)
        return [map_standing_row(row) for row in standings_data]
    except Exception:
        return []


@router.get("/{competition_id}/top-scorers")
async def get_competition_top_scorers(competition_id: int):
    """Returns the top scorers for a competition's current season."""
    season = get_season_year()
    try:
        scorers_data = await _get_top_scorers(competition_id, season)
        return [map_top_scorer(p) for p in scorers_data[:20]]
    except Exception:
        return []


@router.get("/{competition_id}/fixtures")
async def get_competition_fixtures(competition_id: int):
    """Returns upcoming fixtures for a competition's current season."""
    season = get_season_year()
    try:
        today = date.today().isoformat()
        fixtures_data = await football_api.get_fixtures_by_date(today, competition_id, season=season)
        upcoming = [map_match_summary(f) for f in fixtures_data if f.get("status") == "scheduled"]
        return upcoming[:20]
    except Exception:
        return []


@router.get("/{competition_id}/results")
async def get_competition_results(competition_id: int):
    """Returns finished matches (results) for a competition's current season."""
    season = get_season_year()
    try:
        today = date.today().isoformat()
        fixtures_data = await football_api.get_fixtures_by_date(today, competition_id, season=season)
        finished = [map_match_summary(f) for f in fixtures_data if f.get("status") == "finished"]
        return finished[:20]
    except Exception:
        return []
