"""API-Football HTTP client.

Refactored from services/football_api.py — handles raw HTTP calls
only. No mapping or business logic here.
"""

import httpx
from typing import Any

from config import API_KEY, API_HOST, BASE_URL, REQUEST_TIMEOUT
from providers.base import Provider
from providers.api_football.ids import (
    extract_team_external_ids,
    extract_player_external_ids,
    extract_match_external_ids,
    extract_league_external_ids,
)

headers = {
    "x-apisports-key": API_KEY,
}

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    return _client


class APIError(Exception):
    pass


class APIRateLimitError(APIError):
    pass


class APITimeoutError(APIError):
    pass


class APIConnectionError(APIError):
    pass


class APIInvalidResponseError(APIError):
    pass


async def _get(endpoint: str, params: dict[str, Any] | None = None) -> dict:
    """Make a GET request to API-Football."""
    client = _get_client()
    try:
        response = await client.get(endpoint, params=params or {})
    except httpx.TimeoutException as e:
        raise APITimeoutError(f"Request timed out: {e}") from e
    except httpx.ConnectError as e:
        raise APIConnectionError(f"Connection failed: {e}") from e
    except httpx.RequestError as e:
        raise APIError(f"Request failed: {e}") from e

    if response.status_code == 429:
        raise APIRateLimitError("Rate limit exceeded")

    if response.status_code >= 400:
        raise APIError(f"Upstream error {response.status_code}")

    try:
        data = response.json()
    except Exception as e:
        raise APIInvalidResponseError(f"Invalid JSON response: {e}") from e

    if data.get("errors"):
        raise APIInvalidResponseError(f"API error: {data['errors']}")

    return data


class ApiFootballProvider(Provider):
    """API-Football provider implementation."""

    @property
    def name(self) -> str:
        return "api_football"

    async def get_competition(self, competition_id: int) -> dict | None:
        data = await _get("leagues", {"id": competition_id})
        results = data.get("response", [])
        return results[0] if results else None

    async def get_competitions(self) -> list[dict]:
        data = await _get("leagues")
        return data.get("response", [])

    async def get_season(self, competition_id: int, season_label: str) -> dict | None:
        data = await _get("fixtures/season", {"league": competition_id, "season": season_label})
        results = data.get("response", [])
        return results[0] if results else None

    async def get_team(self, team_id: int) -> dict | None:
        data = await _get("teams", {"id": team_id})
        results = data.get("response", [])
        return results[0] if results else None

    async def get_team_players(self, team_id: int, season: int) -> list[dict]:
        data = await _get("players", {"team": team_id, "season": season})
        return data.get("response", [])

    async def get_player(self, player_id: int, season: int) -> dict | None:
        data = await _get("players", {"id": player_id, "season": season})
        results = data.get("response", [])
        return results[0] if results else None

    async def get_fixtures(
        self,
        league_id: int | None = None,
        season: int | None = None,
        date: str | None = None,
        team_id: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if date:
            params["date"] = date
        if team_id:
            params["team"] = team_id
        data = await _get("fixtures", params)
        return data.get("response", [])

    async def get_fixture(self, fixture_id: int) -> dict | None:
        data = await _get("fixtures", {"id": fixture_id})
        results = data.get("response", [])
        return results[0] if results else None

    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        data = await _get("standings", {"league": league_id, "season": season})
        response = data.get("response", [])
        if response:
            return response[0].get("league", {}).get("standings", [[]])[0]
        return []

    async def get_top_scorers(self, league_id: int, season: int) -> list[dict]:
        data = await _get("players/topscorers", {"league": league_id, "season": season})
        return data.get("response", [])

    async def search_team(self, name: str) -> list[dict]:
        data = await _get("teams", {"search": name})
        return data.get("response", [])

    def extract_external_ids(self, entity_type: str, data: Any) -> list[tuple[str, str]]:
        """Extract (provider_name, external_id) pairs from API-Football response."""
        extractors = {
            "team": extract_team_external_ids,
            "player": extract_player_external_ids,
            "match": extract_match_external_ids,
            "competition": extract_league_external_ids,
        }
        extractor = extractors.get(entity_type)
        if extractor is None:
            return []
        return extractor(data)
