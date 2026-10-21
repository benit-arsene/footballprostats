"""
Match-related API endpoints.

Endpoints:
  GET /api/v1/matches/live          — polling feed for in-progress games
  GET /api/v1/matches/live/summary  — matchday window: live + upcoming fixtures
  GET /api/v1/matches/{match_id}    — full match detail
  GET /api/v1/matches/{match_id}/events — chronological event stream
"""

import time

from fastapi import APIRouter, HTTPException

from models import LiveMatchUpdate, MatchDetail, MatchStatus, MatchSummary
from services import football_api
from services.mapper import map_match_detail, map_match_summary
from config import HOME_LEAGUE_IDS, get_season_year

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

# In-memory cache for the matchday window (60-second TTL)
_WINDOW_CACHE: dict[int, dict] = {}
_WINDOW_TTL = 60

# Upcoming fixtures each league contributes to the window
_UPCOMING_LIMIT = 10


async def _league_window(league_id: int) -> list[MatchSummary]:
    """Live matches plus the next upcoming fixtures for one league."""
    now = time.time()
    cached = _WINDOW_CACHE.get(league_id)
    if cached is not None and (now - cached["ts"]) < _WINDOW_TTL:
        return cached["data"]

    fixtures = await football_api.get_live_fixtures(league_id=league_id, season=get_season_year())
    matches = [map_match_summary(f) for f in fixtures]

    live = [m for m in matches if m.status == MatchStatus.LIVE]
    upcoming = sorted(
        (m for m in matches if m.status == MatchStatus.SCHEDULED),
        key=lambda m: (m.date, m.kickoff_time),
    )[:_UPCOMING_LIMIT]

    data = live + upcoming
    _WINDOW_CACHE[league_id] = {"data": data, "ts": now}
    return data


@router.get("/live", response_model=list[LiveMatchUpdate])
async def get_live_matches():
    """
    Polling feed for all active in-progress matches.
    Frontend refetches this every 15-30 seconds during live games.
    """
    try:
        results = []
        for league_id in HOME_LEAGUE_IDS:
            for match in await _league_window(league_id):
                if match.status != MatchStatus.LIVE:
                    continue
                results.append(LiveMatchUpdate(
                    match_id=match.id,
                    slug=match.slug,
                    status=match.status,
                    minute=match.minute or 0,
                    home_score=match.home_score,
                    away_score=match.away_score,
                    events=[],
                    last_event_id=0,
                ))
        return results
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/live/summary", response_model=list[MatchSummary])
async def get_live_matches_summary():
    """
    Matchday window for the featured leagues: live matches first, then the
    next upcoming fixtures. Feeds the homepage match cards and the matchday
    highlights strip.
    """
    try:
        results = []
        for league_id in HOME_LEAGUE_IDS:
            for match in await _league_window(league_id):
                if match.league.id in HOME_LEAGUE_IDS:
                    results.append(match)
        return results
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/date/{date}", response_model=list[MatchSummary])
async def get_matches_by_date(date: str):
    """
    Get fixtures for a specific date (YYYY-MM-DD) for top 5 leagues.
    """
    try:
        season = get_season_year()
        all_fixtures = []
        for league_id in HOME_LEAGUE_IDS:
            fixtures = await football_api.get_fixtures_by_date(date, league_id, season=season)
            all_fixtures.extend(fixtures)
        return [map_match_summary(f) for f in all_fixtures]
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int):
    """
    Core match endpoint: returns full details including teams,
    scores, status, lineups, and current stats.
    """
    try:
        fixture = await football_api.get_fixture(match_id)
        if not fixture:
            raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Match {match_id} not found"}})
        return map_match_detail(fixture)
    except HTTPException:
        raise
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})


@router.get("/{match_id}/events", response_model=MatchDetail)
async def get_match_events(match_id: int):
    """
    Complete chronological event stream for a match.
    Returns the match detail with the full events array ordered by minute.
    """
    try:
        fixture = await football_api.get_fixture(match_id)
        if not fixture:
            raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Match {match_id} not found"}})
        return map_match_detail(fixture)
    except HTTPException:
        raise
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})
