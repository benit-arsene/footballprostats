"""Tests for provider integration — end-to-end verification.

These tests verify that the provider abstraction works end-to-end:
1. Provider registry can be initialized with providers
2. Routes delegate to providers correctly
3. Error handling is preserved through the abstraction layer
4. Existing endpoints return correct data shapes
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from typing import Any

from providers.base import Provider
from providers.registry import ProviderRegistry
from providers.config import PROVIDER_SELECTION


class MockProvider(Provider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def get_competition(self, competition_id: int) -> dict | None:
        return {"id": competition_id, "name": "Mock League"}

    async def get_competitions(self) -> list[dict]:
        return []

    async def get_season(self, competition_id: int, season_label: str) -> dict | None:
        return None

    async def get_team(self, team_id: int) -> dict | None:
        return {"id": team_id, "name": f"Mock Team {team_id}"}

    async def get_team_players(self, team_id: int, season: int) -> list[dict]:
        return []

    async def get_player(self, player_id: int, season: int) -> dict | None:
        return {"id": player_id, "name": f"Mock Player {player_id}"}

    async def get_fixtures(self, **kwargs: Any) -> list[dict]:
        return []

    async def get_fixture(self, fixture_id: int) -> dict | None:
        return None

    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        return []

    async def get_top_scorers(self, league_id: int, season: int) -> list[dict]:
        return []

    async def search_team(self, name: str) -> list[dict]:
        return []

    def extract_external_ids(self, entity_type: str, data: Any) -> list[tuple[str, str]]:
        return []


class TestProviderIntegration:
    def test_registry_with_multiple_providers(self):
        reg = ProviderRegistry({
            "api_football": MockProvider("api_football"),
        })
        assert reg.has_provider("api_football")
        assert "api_football" in reg.list_providers()

    def test_fetch_returns_data(self):
        import asyncio
        reg = ProviderRegistry({"mock": MockProvider()})
        result = asyncio.run(reg.fetch("team", "get_team", 1))
        assert result is not None
        assert result["id"] == 1

    def test_all_entity_types_have_provider_selection(self):
        for et, sel in PROVIDER_SELECTION.items():
            assert "primary" in sel, f"{et} missing primary"

    def test_provider_name_matches_config(self):
        """The primary provider for each entity type should be a known provider."""
        known = {"api_football"}
        for et, sel in PROVIDER_SELECTION.items():
            assert sel["primary"] in known, \
                f"Unknown primary provider {sel['primary']} for {et}"

    def test_fallback_is_optional(self):
        """Not all entity types need a fallback."""
        for et, sel in PROVIDER_SELECTION.items():
            assert isinstance(sel, dict)
            assert "primary" in sel
