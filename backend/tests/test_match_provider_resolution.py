"""Focused tests for match provider resolution via the external_ids mapping.

These tests mock the database session and provider registry so that:
* no external football API is called,
* no API quota is consumed,
* no database connection is required.

They verify that a match ID is only ever sent to the provider that the
external_ids mapping establishes as its owner, and that an un-mapped ID is
rejected with 404 rather than being blindly forwarded to API-Football.
"""

import asyncio
from unittest import mock

import pytest
from fastapi import HTTPException

from routes.matches import _resolve_match_fixture, get_match_detail, get_match_events


class _FakeAsyncSession:
    """Async context manager standing in for a SQLAlchemy AsyncSession."""

    def __init__(self, result):
        self.result = result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        return self.result


def _make_result(ext_row):
    result = mock.MagicMock()
    result.scalar_one_or_none.return_value = ext_row
    return result


def _make_ext(provider: str | None, external_id: str = "101"):
    ext = mock.MagicMock()
    ext.provider = provider
    ext.external_id = external_id
    return ext


def _make_provider(name: str, fixture):
    provider = mock.MagicMock()
    provider.name = name
    provider.get_fixture = mock.AsyncMock(return_value=fixture)
    return provider


def _make_registry_with(providers: dict):
    registry = mock.MagicMock()

    def get_provider(name):
        if name not in providers:
            raise ValueError(f"unknown provider {name}")
        return providers[name]

    registry.has_provider.side_effect = lambda name: name in providers
    registry.get_provider.side_effect = get_provider
    return registry


def _patch_session(ext_row):
    session = _FakeAsyncSession(_make_result(ext_row))
    return mock.patch("routes.matches.async_session", mock.MagicMock(return_value=session))


_API_FOOTBALL_FIXTURE = {
    "fixture": {
        "id": 101,
        "date": "2026-08-22T15:00:00Z",
        "status": {"short": "1H", "elapsed": 23},
        "venue": {"name": "Emirates Stadium"},
        "referee": "Michael Oliver",
    },
    "league": {
        "id": 39,
        "name": "Premier League",
        "logo": "",
        "country": {"name": "England"},
    },
    "teams": {
        "home": {"id": 42, "name": "Arsenal"},
        "away": {"id": 43, "name": "Chelsea"},
    },
    "goals": {"home": 2, "away": 1},
    "events": [],
    "lineups": [],
    "statistics": [],
}


class TestResolveMatchFixture:
    def test_uses_mapped_provider_and_not_api_football(self):
        """A mapped match ID routes only to the provider that owns it."""
        api_football = _make_provider("api_football", {"id": 999})
        football_data = _make_provider("football_data", {"id": 101})
        ext = _make_ext("football_data", "101")
        registry = _make_registry_with(
            {"api_football": api_football, "football_data": football_data}
        )

        with _patch_session(ext), mock.patch("routes.matches._registry", registry):
            result = asyncio.run(_resolve_match_fixture(101))

        assert result == {"id": 101}
        football_data.get_fixture.assert_awaited_once_with(101)
        api_football.get_fixture.assert_not_awaited()

    def test_no_mapping_returns_none_never_falls_back(self):
        """An un-mapped ID returns None; no provider is ever consulted."""
        api_football = _make_provider("api_football", {"id": 101})
        football_data = _make_provider("football_data", {"id": 101})
        registry = _make_registry_with(
            {"api_football": api_football, "football_data": football_data}
        )

        with _patch_session(None), mock.patch("routes.matches._registry", registry):
            result = asyncio.run(_resolve_match_fixture(101))

        assert result is None
        api_football.get_fixture.assert_not_awaited()
        football_data.get_fixture.assert_not_awaited()

    def test_mapped_but_provider_not_registered_returns_none(self):
        """A mapping to an unregistered provider is treated as unresolvable."""
        ext = _make_ext("football_data", "101")
        registry = _make_registry_with({"api_football": _make_provider("api_football", None)})

        with _patch_session(ext), mock.patch("routes.matches._registry", registry):
            result = asyncio.run(_resolve_match_fixture(101))

        assert result is None


class TestMatchDetailAndEvents:
    def test_get_match_detail_returns_404_when_no_mapping(self):
        """Un-mapped IDs are rejected with 404, never forwarded to a provider."""
        with mock.patch(
            "routes.matches._resolve_match_fixture", mock.AsyncMock(return_value=None)
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_match_detail(101))
        assert exc.value.status_code == 404
        assert exc.value.detail["error"]["code"] == "NOT_FOUND"

    def test_get_match_events_returns_404_when_no_mapping(self):
        """Events endpoint mirrors the detail endpoint's 404 behaviour."""
        with mock.patch(
            "routes.matches._resolve_match_fixture", mock.AsyncMock(return_value=None)
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_match_events(101))
        assert exc.value.status_code == 404

    def test_get_match_detail_returns_mapped_detail(self):
        """When a mapping resolves a fixture, the detail is mapped and returned."""
        from services.mapper import map_match_detail

        expected = map_match_detail(_API_FOOTBALL_FIXTURE)
        with mock.patch(
            "routes.matches._resolve_match_fixture",
            mock.AsyncMock(return_value=_API_FOOTBALL_FIXTURE),
        ):
            result = asyncio.run(get_match_detail(101))
        assert result == expected

    def test_get_match_detail_returns_429_on_upstream_rate_limit(self):
        """Upstream rate-limit errors surface as HTTP 429 for either provider."""

        class APIRateLimitError(Exception):
            pass

        with mock.patch(
            "routes.matches._resolve_match_fixture",
            mock.AsyncMock(side_effect=APIRateLimitError("rate limited")),
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_match_detail(101))
        assert exc.value.status_code == 429
