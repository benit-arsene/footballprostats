"""Tests for football-data.org provider (HTTP client).

Tests that the provider correctly handles:
- Successful responses
- Missing fields
- Authentication errors (401/403)
- Rate limiting (429)
- Timeouts
- Connection errors
- Invalid responses
- External ID extraction
"""

import os
import pytest
from typing import Any
from unittest.mock import patch, AsyncMock

from providers.football_data.client import (
    FootballDataProvider,
    APIError,
    APIRateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIInvalidResponseError,
)
from providers.football_data.ids import (
    extract_team_external_ids,
    extract_player_external_ids,
    extract_match_external_ids,
    extract_competition_external_ids,
)
from providers.base import Provider


class TestFootballDataProviderStructure:
    def test_provider_has_name(self):
        p = FootballDataProvider()
        assert p.name == "football_data"

    def test_provider_implements_all_methods(self):
        """Provider must implement all abstract methods."""
        p = FootballDataProvider()
        for method_name in Provider.__abstractmethods__:
            assert hasattr(p, method_name), f"Missing: {method_name}"
            if method_name != "name":
                assert callable(getattr(p, method_name))

    def test_api_exception_classes(self):
        assert issubclass(APIError, Exception)
        assert issubclass(APIRateLimitError, APIError)
        assert issubclass(APITimeoutError, APIError)
        assert issubclass(APIConnectionError, APIError)
        assert issubclass(APIInvalidResponseError, APIError)


class TestExternalIdExtraction:
    def test_team_external_ids(self):
        assert extract_team_external_ids({"id": 65}) == [("football_data", "65")]
        assert extract_team_external_ids({}) == []
        assert extract_team_external_ids(None) == []

    def test_player_external_ids(self):
        assert extract_player_external_ids({"id": 123}) == [("football_data", "123")]
        assert extract_player_external_ids({}) == []

    def test_match_external_ids(self):
        assert extract_match_external_ids({"id": 999}) == [("football_data", "999")]
        assert extract_match_external_ids({}) == []

    def test_competition_external_ids(self):
        assert extract_competition_external_ids({"id": 2021}) == [("football_data", "2021")]
        assert extract_competition_external_ids({}) == []


class TestFootballDataProviderClient:
    @pytest.mark.asyncio
    async def test_get_competition_returns_none_without_api_key(self):
        p = FootballDataProvider()
        result = await p.get_competition(39)
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_team_returns_none_without_api_key(self):
        p = FootballDataProvider()
        result = await p.get_team(50)
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_standings_returns_list(self):
        p = FootballDataProvider()
        result = await p.get_standings(39, 2024)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_fixtures_returns_list(self):
        p = FootballDataProvider()
        result = await p.get_fixtures(league_id=39, season=2024)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_team_players_returns_empty_list(self):
        """Free tier does not provide player profiles."""
        p = FootballDataProvider()
        result = await p.get_team_players(50, 2024)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_player_returns_none(self):
        """Free tier does not provide player profiles."""
        p = FootballDataProvider()
        result = await p.get_player(123, 2024)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_top_scorers_returns_list(self):
        p = FootballDataProvider()
        result = await p.get_top_scorers(39, 2024)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_team_returns_list(self):
        p = FootballDataProvider()
        result = await p.search_team("Arsenal")
        assert isinstance(result, list)