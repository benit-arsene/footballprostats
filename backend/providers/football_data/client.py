"""football-data.org HTTP client and provider implementation.

Base URL: https://api.football-data.org/v4
Auth: X-Auth-Token header
"""

import httpx
from typing import Any

from config import REQUEST_TIMEOUT
from providers.base import Provider
from providers.football_data.ids import (
    extract_team_external_ids,
    extract_player_external_ids,
    extract_match_external_ids,
    extract_competition_external_ids,
)
from providers.football_data.adapters import (
    FootballDataAdapters,
    COMPETITION_CODE_MAP,
    CODE_TO_COMPETITION_ID,
)

BASE_URL = "https://api.football-data.org/v4"

# The v4 scorers subresource defaults to limit=10. Request a limit high enough
# to return every recorded goalscorer for the competition in one call.
SCORERS_LIMIT = 500

# Mapping from internal competition IDs to football-data.org competition codes
# (duplicated here for client use; adapters also define these).

HEADERS: dict[str, str] = {}


def _get_headers() -> dict[str, str]:
    import os
    key = os.getenv("FOOTBALLDATA_KEY", "")
    return {"X-Auth-Token": key}


_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=_get_headers(),
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
    """Make a GET request to football-data.org."""
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

    if isinstance(data, dict) and data.get("error"):
        raise APIInvalidResponseError(f"API error: {data['error']}")

    return data


def _comp_code(competition_id: int) -> str | None:
    return COMPETITION_CODE_MAP.get(competition_id)


class FootballDataProvider(Provider):
    """football-data.org provider implementation."""

    @property
    def name(self) -> str:
        return "football_data"

    async def get_competition(self, competition_id: int) -> dict | None:
        code = _comp_code(competition_id)
        if not code:
            return None
        try:
            data = await _get(f"/competitions/{code}")
            return data
        except APIError:
            return None

    async def get_competitions(self) -> list[dict]:
        try:
            data = await _get("/competitions")
            return data.get("competitions", [])
        except APIError:
            return []

    async def get_season(self, competition_id: int, season_label: str) -> dict | None:
        # football-data.org doesn't have a separate season endpoint;
        # season info comes from the competition endpoint.
        return await self.get_competition(competition_id)

    async def get_team(self, team_id: int) -> dict | None:
        try:
            data = await _get(f"/teams/{team_id}")
            return data
        except APIError:
            return None

    async def get_team_players(self, team_id: int, season: int) -> list[dict]:
        # Free tier does not provide squad/player profiles.
        return []

    async def get_player(self, player_id: int, season: int) -> dict | None:
        # Free tier does not provide player profiles.
        return None

    async def get_fixtures(
        self,
        league_id: int | None = None,
        season: int | None = None,
        date: str | None = None,
        team_id: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if league_id:
            code = _comp_code(league_id)
            if not code:
                return []
            endpoint = f"/competitions/{code}/matches"
        elif team_id:
            endpoint = f"/teams/{team_id}/matches"
        else:
            return []

        if season:
            params["season"] = season
        if date:
            params["dateFrom"] = date
            params["dateTo"] = date

        try:
            data = await _get(endpoint, params)
            return data.get("matches", [])
        except APIError:
            return []

    async def get_fixture(self, fixture_id: int) -> dict | None:
        try:
            data = await _get(f"/matches/{fixture_id}")
            return data
        except APIError:
            return None

    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        code = _comp_code(league_id)
        if not code:
            return []
        try:
            data = await _get(f"/competitions/{code}/standings", {"season": season})
            standings = data.get("standings", [])
            # Return the TOTAL standings table
            for s in standings:
                if s.get("type") == "TOTAL":
                    return s.get("table", [])
            return standings[0].get("table", []) if standings else []
        except APIError:
            return []

    async def get_top_scorers_payload(self, league_id: int, season: int) -> dict:
        """Full scorers response: rows plus provider context (count, season)."""
        code = _comp_code(league_id)
        if not code:
            return {}
        try:
            data = await _get(
                f"/competitions/{code}/scorers",
                {"season": season, "limit": SCORERS_LIMIT},
            )
            return data
        except APIError:
            return {}

    async def get_top_scorers(self, league_id: int, season: int) -> list[dict]:
        payload = await self.get_top_scorers_payload(league_id, season)
        return payload.get("scorers", [])

    async def search_team(self, name: str) -> list[dict]:
        # football-data.org doesn't have a search endpoint; return empty
        return []

    def extract_external_ids(self, entity_type: str, data: Any) -> list[tuple[str, str]]:
        extractors = {
            "team": extract_team_external_ids,
            "player": extract_player_external_ids,
            "match": extract_match_external_ids,
            "competition": extract_competition_external_ids,
        }
        extractor = extractors.get(entity_type)
        if extractor is None:
            return []
        if isinstance(data, list):
            return [pair for item in data for pair in extractor(item)]
        return extractor(data)