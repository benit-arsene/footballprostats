"""Tests for season-aware provider routing policy."""

import os
from unittest import mock

from providers.routing import (
    route_provider,
    is_current_season,
    current_season_label,
    is_football_data_available,
    FOOTBALL_DATA_SUPPORTED,
)


class TestIsCurrentSeason:
    def test_current_season_label(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            label = current_season_label()
            assert label == "2026/2027"

    def test_current_season_matches(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            assert is_current_season("2026/2027") is True

    def test_historical_season_rejected(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            assert is_current_season("2024/2025") is False

    def test_missing_label_rejected(self):
        assert is_current_season(None) is False
        assert is_current_season("") is False

    def test_malformed_label_rejected(self):
        assert is_current_season("2026") is False
        assert is_current_season("abc/def") is False
        assert is_current_season("2026/2028") is False


class TestRouteProvider:
    def test_current_season_fixtures_selects_football_data_when_registered(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "match",
                season_label="2026/2027",
                data_type="fixtures",
                available_providers={"api_football", "football_data"},
            )
            assert result == "football_data"

    def test_current_season_standings_selects_football_data_when_registered(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "standings",
                season_label="2026/2027",
                data_type="standings",
                available_providers={"api_football", "football_data"},
            )
            assert result == "football_data"

    def test_historical_season_fixtures_selects_api_football(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "match",
                season_label="2024/2025",
                data_type="fixtures",
                available_providers={"api_football", "football_data"},
            )
            assert result == "api_football"

    def test_missing_season_label_selects_api_football(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "match",
                season_label=None,
                data_type="fixtures",
                available_providers={"api_football", "football_data"},
            )
            assert result == "api_football"

    def test_malformed_season_label_selects_api_football(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "match",
                season_label="bad",
                data_type="fixtures",
                available_providers={"api_football", "football_data"},
            )
            assert result == "api_football"

    def test_unsupported_data_type_selects_api_football(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            for dt in ("player", "match_events", "competition"):
                result = route_provider(
                    dt,
                    season_label="2026/2027",
                    data_type=dt,
                    available_providers={"api_football", "football_data"},
                )
                assert result == "api_football", f"expected api_football for {dt}"

    def test_missing_football_data_registration_selects_api_football(self):
        with mock.patch("providers.routing.get_season_year", return_value=2026):
            result = route_provider(
                "match",
                season_label="2026/2027",
                data_type="fixtures",
                available_providers={"api_football"},
            )
            assert result == "api_football"

    def test_existing_api_football_selection_unchanged(self):
        # PROVIDER_SELECTION still maps all entity types to api_football primary
        from providers.config import PROVIDER_SELECTION
        for et, sel in PROVIDER_SELECTION.items():
            assert sel["primary"] == "api_football", f"{et} primary changed"
