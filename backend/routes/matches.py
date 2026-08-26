"""
Match-related API endpoints.

Endpoints:
  GET /api/v1/matches/live          — polling feed for in-progress games
  GET /api/v1/matches/{match_id}    — full match detail
  GET /api/v1/matches/{match_id}/events — chronological event stream
"""

from fastapi import APIRouter, HTTPException

from models import LiveMatchUpdate, MatchDetail, MatchSummary
from services import football_api
from services.mapper import map_match_detail, map_match_summary

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/live", response_model=list[LiveMatchUpdate])
async def get_live_matches():
    """
    Polling feed for all active in-progress matches.
    Frontend refetches this every 15-30 seconds during live games.
    """
    try:
        fixtures = await football_api.get_live_fixtures()
        results = []
        for fixture in fixtures[:20]:
            detail = map_match_detail(fixture)
            results.append(LiveMatchUpdate(
                match_id=detail.id,
                slug=detail.slug,
                status=detail.status,
                minute=detail.minute or 0,
                home_score=detail.home_score,
                away_score=detail.away_score,
                events=[],
                last_event_id=detail.events[-1].id if detail.events else 0,
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


@router.get("/live/summary", response_model=list[MatchSummary])
async def get_live_matches_summary():
    """
    Live matches as MatchSummary (for homepage cards).
    Filters to top 5 European leagues.
    """
    TOP_LEAGUES = {39, 140}  # PL, La Liga only
    try:
        fixtures = await football_api.get_live_fixtures()
        results = []
        for fixture in fixtures:
            league_id = fixture.get("league", {}).get("id")
            if league_id in TOP_LEAGUES:
                results.append(map_match_summary(fixture))
        return results
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


@router.get("/date/{date}", response_model=list[MatchSummary])
async def get_matches_by_date(date: str):
    """
    Get fixtures for a specific date (YYYY-MM-DD) for top 5 leagues.
    """
    TOP_LEAGUES = {39, 140}  # PL, La Liga only
    try:
        all_fixtures = []
        for league_id in TOP_LEAGUES:
            fixtures = await football_api.get_fixtures_by_date(date, league_id)
            all_fixtures.extend(fixtures)
        return [map_match_summary(f) for f in all_fixtures]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int):
    """
    Core match endpoint: returns full details including teams,
    scores, status, lineups, and current stats.
    """
    try:
        fixture = await football_api.get_fixture(match_id)
        if not fixture:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
        return map_match_detail(fixture)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


@router.get("/{match_id}/events", response_model=MatchDetail)
async def get_match_events(match_id: int):
    """
    Complete chronological event stream for a match.
    Returns the match detail with the full events array ordered by minute.
    """
    try:
        fixture = await football_api.get_fixture(match_id)
        if not fixture:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
        return map_match_detail(fixture)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")
