"""Offline tests for backend/ingestion/runner.py."""
import asyncio
from unittest import mock

import pytest

import ingestion.runner as runner_mod
from ingestion.fixtures import FixtureIngestionResult


class _Session:
    def __init__(self):
        self.commit = mock.AsyncMock()
        self.rollback = mock.AsyncMock()
        self.close = mock.AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _run(coro):
    return asyncio.run(coro)


def test_success_commits():
    session = _Session()

    def factory():
        return session

    result = FixtureIngestionResult(created=1, records_processed=1)

    with mock.patch.object(runner_mod, "ingest_fixtures", new=mock.AsyncMock(return_value=result)) as m:
        out = _run(runner_mod.run_fixture_ingestion(
            "api_football", 1, 5, 1, season_year=2026, session_factory=factory
        ))
    assert out is result
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    m.assert_awaited_once()


def test_fatal_error_rolls_back_and_propagates():
    session = _Session()

    def factory():
        return session

    with mock.patch.object(runner_mod, "ingest_fixtures", new=mock.AsyncMock(side_effect=RuntimeError("boom"))):
        with pytest.raises(RuntimeError, match="boom"):
            _run(runner_mod.run_fixture_ingestion("api_football", 1, 5, 1, session_factory=factory))
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
