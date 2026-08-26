"""
API-Football client service.

Wraps https://v3.football.api-sports.io and returns raw JSON responses.
Uses httpx for async HTTP calls.

Free tier: 100 requests/day — keep this in mind.
"""

import os
import httpx
from typing import Any

API_KEY = os.getenv("APIFOOTBALL_KEY", "")
API_HOST = os.getenv("APIFOOTBALL_HOST", "v3.football.api-sports.io")
BASE_URL = f"https://{API_HOST}"

# Default league IDs for our mock data
LEAGUE_IDS = {
    "premier-league": 39,
    "la-liga": 140,
    "champions-league": 2,
    "bundesliga": 78,
    "serie-a": 135,
}

headers = {
    "x-apisports-key": API_KEY,
}


async def _get(endpoint: str, params: dict[str, Any] | None = None) -> dict:
    """Make a GET request to API-Football."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            params=params or {},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        # API-Football wraps responses in { "get": ..., "response": [...] }
        if data.get("errors"):
            raise ValueError(f"API error: {data['errors']}")

        return data


# ─── Match / Fixture endpoints ───────────────────────────────────────

async def get_fixture(fixture_id: int) -> dict | None:
    """
    Get full fixture details: teams, score, events, lineups, statistics.
    This is the main endpoint for match detail pages.
    """
    data = await _get("fixtures", {"id": fixture_id})
    results = data.get("response", [])
    return results[0] if results else None


async def get_live_fixtures(league_id: int | None = None) -> list[dict]:
    """
    Get all currently live fixtures.
    Used for the live ticker on the home page.
    """
    params: dict[str, Any] = {"live": "all"}
    if league_id:
        params["league"] = league_id
    data = await _get("fixtures", params)
    return data.get("response", [])


async def get_fixtures_by_date(date: str, league_id: int | None = None) -> list[dict]:
    """
    Get fixtures for a specific date (YYYY-MM-DD).
    Used for the home page match list.
    """
    params: dict[str, Any] = {"date": date}
    if league_id:
        params["league"] = league_id
    data = await _get("fixtures", params)
    return data.get("response", [])


async def get_fixtures_by_team(
    team_id: int, season: int, league_id: int | None = None
) -> list[dict]:
    """Get all fixtures for a team in a season."""
    params: dict[str, Any] = {"team": team_id, "season": season}
    if league_id:
        params["league"] = league_id
    data = await _get("fixtures", params)
    return data.get("response", [])


# ─── Team endpoints ──────────────────────────────────────────────────

async def get_team(team_id: int) -> dict | None:
    """Get team information."""
    data = await _get("teams", {"id": team_id})
    results = data.get("response", [])
    return results[0] if results else None


async def get_team_players(team_id: int, season: int) -> list[dict]:
    """Get squad/players for a team."""
    data = await _get("players", {"team": team_id, "season": season})
    return data.get("response", [])


async def search_team(name: str) -> list[dict]:
    """Search for a team by name."""
    data = await _get("teams", {"search": name})
    return data.get("response", [])


# ─── Player endpoints ────────────────────────────────────────────────

async def get_player(player_id: int, season: int) -> dict | None:
    """Get player profile and stats."""
    data = await _get("players", {"id": player_id, "season": season})
    results = data.get("response", [])
    return results[0] if results else None


async def get_player_trophies(player_id: int) -> list[dict]:
    """Get player trophies."""
    data = await _get("players/trophies", {"player": player_id})
    return data.get("response", [])


# ─── League endpoints ────────────────────────────────────────────────

async def get_league(league_id: int, season: int) -> dict | None:
    """Get league info."""
    data = await _get("leagues", {"id": league_id, "season": season})
    results = data.get("response", [])
    return results[0] if results else None


async def get_standings(league_id: int, season: int) -> list[dict]:
    """Get league standings table."""
    data = await _get("standings", {"league": league_id, "season": season})
    response = data.get("response", [])
    if response:
        return response[0].get("league", {}).get("standings", [[]])[0]
    return []


async def get_top_scorers(league_id: int, season: int) -> list[dict]:
    """Get top scorers for a league."""
    data = await _get("players/topscorers", {"league": league_id, "season": season})
    return data.get("response", [])


# ─── Utilities ───────────────────────────────────────────────────────

def get_season_year() -> int:
    """Get the current season year (approximate)."""
    from datetime import datetime
    now = datetime.now()
    # Football seasons typically run Aug-May
    if now.month >= 8:
        return now.year
    return now.year - 1
