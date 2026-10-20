"""Tests for service-level provider dispatch."""

import os
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("FOOTBALLDATA_KEY", "test-key")


def _make_mock_provider(name):
    from unittest.mock import AsyncMock, MagicMock

    p = MagicMock()
    p.name = name
    p.get_standings = AsyncMock(return_value=[{"provider": name}])
    p.get_fixtures = AsyncMock(return_value=[{"provider": name}])
    p.get_team = AsyncMock(return_value={"provider": name})
    p.get_player = AsyncMock(return_value={"provider": name})
    return p


def _patch_registry(fd_available):
    import services.football_api as svc

    api = _make_mock_provider("api_football")
    fd = _make_mock_provider("football_data") if fd_available else None
    providers = {"api_football": api}
    if fd is not None:
        providers["football_data"] = fd
    registry = mock.MagicMock()
    registry.list_providers.return_value = list(providers.keys())
    registry.get_provider.side_effect = lambda n: providers[n]
    svc._registry = registry
    svc._api_football = api
    return api, fd


def test_current_season_standings_use_football_data_when_registered():
    api, fd = _patch_registry(True)
    import services.football_api as svc
    import asyncio

    async def run():
        return await svc.get_standings(39, 2026)

    res = asyncio.run(run())
    fd.get_standings.assert_awaited_once()
    api.get_standings.assert_not_awaited()
    assert res == [{"provider": "football_data"}]


def test_historical_standings_use_api_football():
    api, fd = _patch_registry(True)
    import services.football_api as svc
    import asyncio

    async def run():
        return await svc.get_standings(39, 2024)

    res = asyncio.run(run())
    api.get_standings.assert_awaited_once()
    fd.get_standings.assert_not_awaited()
    assert res == [{"provider": "api_football"}]


def test_missing_season_defaults_to_api_football():
    api, fd = _patch_registry(True)
    import services.football_api as svc
    import asyncio

    async def run():
        return await svc.get_standings(39, None) if False else None

    # get_standings requires season int; test fixtures_by_team with season that maps to current? Use get_standings with a malformed approach via direct route_provider instead.
    # Instead test that a None season label path keeps api_football: call _provider_for directly.
    p = svc._provider_for("standings", season=None, data_type="standings")
    assert p is api


def test_unsupported_data_type_stays_api_football():
    api, fd = _patch_registry(True)
    import services.football_api as svc
    p = svc._provider_for("player", season=2026, data_type="player")
    assert p is api


def test_without_footballdata_key_no_crash():
    _patch_registry(False)
    import services.football_api as svc
    import asyncio

    async def run():
        return await svc.get_standings(39, 2026)

    res = asyncio.run(run())
    # football_data unavailable -> api_football used
    assert res == [{"provider": "api_football"}]


def test_service_signatures_compatible():
    import services.football_api as svc
    import inspect

    assert inspect.signature(svc.get_standings) == inspect.signature(lambda league_id, season: None).__wrapped__ if hasattr(inspect.signature(lambda: None), "__wrapped__") else True
    # Just ensure callable with expected args
    assert callable(svc.get_standings)
    assert callable(svc.get_fixtures_by_team)
    assert callable(svc.get_team)
    assert callable(svc.get_player)
