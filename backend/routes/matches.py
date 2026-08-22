"""
Match-related API endpoints.

Endpoints:
  GET /api/v1/matches/live          — polling feed for in-progress games
  GET /api/v1/matches/{match_id}    — full match detail
  GET /api/v1/matches/{match_id}/events — chronological event stream
"""

from fastapi import APIRouter, HTTPException

from models import LiveMatchUpdate, MatchDetail

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/live", response_model=list[LiveMatchUpdate])
async def get_live_matches():
    """
    Polling feed for all active in-progress matches.

    Frontend refetches this every 15-30 seconds during live games.
    Returns lightweight payloads with only the delta since the last
    known event (identified by `last_event_id`).
    """
    # TODO: Query PostgreSQL for matches WHERE status = 'live'
    # For now, return empty list as placeholder
    return []


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int):
    """
    Core match endpoint: returns full details including teams,
    scores, status, lineups, and current stats.

    For finished matches the data is served from PostgreSQL cache,
    keeping page loads fast for search engine crawlers.
    """
    # TODO: Query PostgreSQL by match_id
    raise HTTPException(status_code=404, detail=f"Match {match_id} not found")


@router.get("/{match_id}/events", response_model=MatchDetail)
async def get_match_events(match_id: int):
    """
    Complete chronological event stream for a match.

    This is the PCS-style incident ticker data. Returns the match
    detail with the full events array ordered by minute.

    Finished matches serve cached event data from PostgreSQL to
    keep page load times fast for search engine crawlers.
    """
    # TODO: Query PostgreSQL for match + events by match_id
    raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
