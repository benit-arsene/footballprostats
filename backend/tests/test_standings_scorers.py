"""Tests for standings competition resolution (no network, no database).

The live top scorers endpoint is keyed by the internal competition id, but
provider-side competition ids are accepted too. These tests pin that mapping
so a caller can never end up with an empty scorer table again.
"""

import asyncio
import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import standings as st


PREMIER_LEAGUE = SimpleNamespace(
    entity_type="competition", provider="api_football", external_id="39", competition_id=1
)
LA_LIGA = SimpleNamespace(
    entity_type="competition", provider="football_data", external_id="PD", competition_id=2
)


def _filters(stmt) -> dict:
    """WHERE criteria of a select statement, keyed by column name."""
    filters = {}
    for key, value in stmt.compile().params.items():
        filters[key.rsplit("_", 1)[0]] = value
    return filters


def _matches(row, filters: dict) -> bool:
    if filters.get("entity_type") != row.entity_type:
        return False
    if "competition_id" in filters and filters["competition_id"] != row.competition_id:
        return False
    if "external_id" in filters and filters["external_id"] != row.external_id:
        return False
    if "provider" in filters and filters["provider"] != row.provider:
        return False
    return True


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, stmt):
        filters = _filters(stmt)
        return _FakeResult([r for r in self._rows if _matches(r, filters)])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _make_session(rows):
    def factory():
        return _FakeSession(rows)

    return factory


@pytest.fixture
def competitions(monkeypatch):
    rows = [PREMIER_LEAGUE, LA_LIGA]
    monkeypatch.setattr(st, "async_session", _make_session(rows))
    return rows


def test_internal_competition_id_resolves_to_provider_id(competitions):
    """Internal ids (Premier League = 1, La Liga = 2) resolve to provider ids."""
    assert asyncio.run(st._resolve_scorers_competition_id(1)) == 39
    assert asyncio.run(st._resolve_scorers_competition_id(2)) == 140


def test_provider_competition_id_is_accepted(competitions):
    """Provider-side competition ids keep working for existing callers."""
    assert asyncio.run(st._resolve_scorers_competition_id(39)) == 39
    assert asyncio.run(st._resolve_scorers_competition_id(140)) == 140


def test_unknown_competition_raises_not_found(competitions):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(st._resolve_scorers_competition_id(999))
    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "NOT_FOUND"


def test_top_scorers_route_is_registered():
    from main import app

    paths = {r.path for r in app.routes}
    assert "/api/v1/standings/top-scorers-live" in paths
    assert "/api/v1/leagues/{league_id}" in paths
