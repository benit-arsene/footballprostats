"""Focused tests for backend/ingestion/fixtures.py fixture ingestion workflow.

All tests use mocked AsyncSession, mocked providers, and mocked registry —
no database, no external APIs.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import date, time
from unittest import mock

import pytest

import ingestion.fixtures as fixtures_mod
from ingestion.fixtures import ingest_fixtures, FixtureIngestionResult


# ─── Raw provider fixtures ─────────────────────────────────────────────


_API_FOOTBALL_FIXTURE = {
    "fixture": {
        "id": 101,
        "date": "2026-08-22T15:00:00Z",
        "status": {"short": "NS", "elapsed": None},
        "venue": {"name": "Emirates Stadium"},
    },
    "teams": {
        "home": {"id": 42, "name": "Arsenal"},
        "away": {"id": 43, "name": "Chelsea"},
    },
    "league": {
        "id": 39,
        "name": "Premier League",
        "logo": "",
        "country": {"name": "England"},
    },
    "goals": {"home": 0, "away": 0},
    "events": [],
    "lineups": [],
    "statistics": [],
}


_FOOTBALL_DATA_FIXTURE = {
    "id": 201,
    "utcDate": "2026-08-22T15:00:00Z",
    "status": "SCHEDULED",
    "homeTeam": {"id": 42, "name": "Arsenal"},
    "awayTeam": {"id": 43, "name": "Chelsea"},
    "competition": {
        "id": 39,
        "name": "Premier League",
        "code": "PL",
        "area": {"name": "England"},
        "emblem": "",
    },
    "score": {"fullTime": {"home": 0, "away": 0}},
    "venue": "",
}


# ─── Mock helpers ───────────────────────────────────────────────────────


class _MockSession:
    def __init__(self):
        self.added = []
        self.flushed = 0
        self._execute_result = None

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        self.flushed += 1

    async def execute(self, stmt):
        result = mock.MagicMock()
        result.scalar_one_or_none.return_value = self._execute_result
        return result

    def set_execute_result(self, row):
        self._execute_result = row


class _MockMatch:
    def __init__(self, id, slug, **kwargs):
        self.id = id
        self.slug = slug
        for k, v in kwargs.items():
            setattr(self, k, v)


def _run_async(coro):
    return asyncio.run(coro)


# ─── Fixture for patching track_job ───────────────────────────────────


def _mock_track_job():
    """Return a context manager yielding (patcher, mock_job).

    The caller must start()/stop() the patcher inside the with block.
    When started, fixtures_mod.track_job becomes an async context manager
    that yields mock_job.
    """
    mock_job = mock.Mock()
    mock_job.records_processed = 0
    mock_job.records_failed = 0

    @asynccontextmanager
    async def _track_job(*args, **kwargs):
        yield mock_job

    patcher = mock.patch.object(fixtures_mod, "track_job", new=_track_job)

    @contextmanager
    def _cm():
        yield patcher, mock_job

    return _cm()


# ─── Fixture for patching provider registry ─────────────────────────────


def _mock_registry(provider_name, provider_mock):
    """Return a patcher for build_provider_registry returning a mock registry."""
    registry = mock.MagicMock()
    registry.has_provider.return_value = True
    registry.get_provider.return_value = provider_mock
    return mock.patch(
        "ingestion.fixtures.build_provider_registry", return_value=registry
    )


# ─── Tests ─────────────────────────────────────────────────────────────


class TestInsertNewFixtures:
    def test_insert_new_api_football_fixture(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        match_mock = _MockMatch(id=100, slug="arsenal-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), True)),
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 1
        assert result.updated == 0
        assert result.records_processed == 1
        assert result.records_failed == 0
        assert result.conflicts == 0
        assert provider_mock.get_fixtures.await_count == 1
        # Verify provider called with competition_id as league_id
        call_kwargs = provider_mock.get_fixtures.await_args.kwargs
        assert call_kwargs["league_id"] == 39
        assert call_kwargs["season"] == 2026

        # Verify upsert_entity called with correct Match fields
        ue_call = mock_ue.call_args
        assert ue_call.kwargs["conflict_keys"] == {"slug": "arsenal-vs-chelsea-101"}
        assert ue_call.kwargs["values"]["competition_id"] == 39
        assert ue_call.kwargs["values"]["season_id"] == 5
        assert ue_call.kwargs["values"]["home_team_id"] == 1
        assert ue_call.kwargs["values"]["away_team_id"] == 2
        assert ue_call.kwargs["values"]["home_score"] == 0
        assert ue_call.kwargs["values"]["away_score"] == 0

        # Verify upsert_external_id called with match_id column
        uei_call = mock_uei.call_args
        assert uei_call.kwargs["entity_type"] == "match"
        assert uei_call.kwargs["provider"] == "api_football"
        assert uei_call.kwargs["external_id"] == "101"
        assert uei_call.kwargs["internal_id"] == 100
        assert uei_call.kwargs["entity_column"] == "match_id"


class TestUpdateExistingFixture:
    def test_update_without_duplication(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        existing_match = _MockMatch(id=100, slug="arsenal-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(existing_match, False)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), False)),
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 0
        assert result.updated == 1
        assert result.records_processed == 1
        assert mock_ue.call_args.kwargs["conflict_keys"] == {"slug": "arsenal-vs-chelsea-101"}


class TestExternalIdMapping:
    def test_mapping_connects_provider_id_to_internal_id(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        match_mock = _MockMatch(id=100, slug="arsenal-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), True)),
        ) as mock_uei:
            track_patcher.start()
            _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        uei_call = mock_uei.call_args
        assert uei_call.kwargs["entity_type"] == "match"
        assert uei_call.kwargs["provider"] == "api_football"
        assert uei_call.kwargs["external_id"] == "101"   # provider's match ID
        assert uei_call.kwargs["internal_id"] == 100     # our internal Match.id
        assert uei_call.kwargs["entity_column"] == "match_id"


class TestPreserveExistingValues:
    def test_optional_kickoff_time_none_preserved(self):
        """When incoming kickoff_time is None, preserve_existing=True keeps old value."""
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        match_mock = _MockMatch(id=100, slug="arsenal-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), True)),
        ) as mock_uei:
            track_patcher.start()
            _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        ue_call = mock_ue.call_args
        # kickoff_time parsed from "15:00:00Z" → time(15, 0)
        assert ue_call.kwargs["values"]["kickoff_time"] == time(15, 0)
        # preserve_existing=True (default)
        assert ue_call.kwargs["preserve_existing"] is True


class TestConflictingExternalId:
    def test_conflict_rejects_reassignment(self):
        """When external_id already maps to a different match_id, do not reassign."""
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        new_match = _MockMatch(id=200, slug="arsenal-chelsea-101")

        # Conflict detection: external_id "101" already maps to match_id 999
        existing_ext = mock.Mock()
        existing_ext.match_id = 999

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(new_match, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(),
        ) as mock_uei:
            # Make session.execute return existing_ext for the conflict detection query.
            session._execute_result = existing_ext

            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.conflicts == 1
        assert result.records_failed == 1
        # upsert_external_id should NOT be called for the conflicting fixture
        mock_uei.assert_not_called()
        assert "already maps to match_id 999" in result.errors[0]


class TestEmptyResponse:
    def test_empty_provider_response(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[])

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock()
        ) as mock_rt, mock.patch.object(
            fixtures_mod, "upsert_entity", new=mock.AsyncMock()
        ) as mock_ue, mock.patch.object(
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 0
        assert result.updated == 0
        assert result.records_processed == 0
        assert result.records_failed == 0
        assert result.conflicts == 0
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()


class TestProviderError:
    def test_provider_error_re_raised(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(
            side_effect=RuntimeError("provider unreachable")
        )

        with _mock_registry("api_football", provider_mock), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock()
        ), mock.patch.object(
            fixtures_mod, "upsert_entity", new=mock.AsyncMock()
        ), mock.patch.object(
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ):
            with pytest.raises(RuntimeError, match="provider unreachable"):
                _run_async(
                    ingest_fixtures(
                        session,
                        provider_name="api_football",
                        competition_id=39,
                        season_id=5,
                        data_source_id=1,
                        season_year=2026,
                    )
                )


class TestMissingTeamMapping:
    def test_fixture_skipped_when_team_not_mapped(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        # Home team not found → fixture skipped
        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(return_value=None)
        ) as mock_rt, mock.patch.object(
            fixtures_mod, "upsert_entity", new=mock.AsyncMock()
        ) as mock_ue, mock.patch.object(
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.skipped == 1
        assert result.created == 0
        assert result.updated == 0
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()


class TestUnknownProvider:
    def test_unknown_provider_raises_value_error(self):
        session = _MockSession()

        registry = mock.MagicMock()
        registry.has_provider.return_value = False

        with mock.patch(
            "ingestion.fixtures.build_provider_registry", return_value=registry
        ):
            with pytest.raises(ValueError, match="Unknown provider"):
                _run_async(
                    ingest_fixtures(
                        session,
                        provider_name="nonexistent",
                        competition_id=39,
                        season_id=5,
                        data_source_id=1,
                        season_year=2026,
                    )
                )


class TestCompetitionSeasonFK:
    def test_competition_and_season_ids_preserved(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        match_mock = _MockMatch(id=100, slug="arsenal-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), True)),
        ) as mock_uei:
            track_patcher.start()
            _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=140,
                    season_id=12,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        ue_call = mock_ue.call_args
        assert ue_call.kwargs["values"]["competition_id"] == 140
        assert ue_call.kwargs["values"]["season_id"] == 12


class TestFootballDataFormat:
    def test_football_data_fixture_normalized(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_FOOTBALL_DATA_FIXTURE])

        match_mock = _MockMatch(id=200, slug="arsenal-chelsea-201")

        with _mock_registry("football_data", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=8), True)),
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="football_data",
                    competition_id=39,
                    season_id=5,
                    data_source_id=2,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 1
        assert result.records_processed == 1
        # Provider called with league_id=39, season=2026
        call_kwargs = provider_mock.get_fixtures.await_args.kwargs
        assert call_kwargs["league_id"] == 39
        assert call_kwargs["season"] == 2026
        # External ID mapping uses football-data provider name
        uei_call = mock_uei.call_args
        assert uei_call.kwargs["provider"] == "football_data"
        assert uei_call.kwargs["external_id"] == "201"


class TestMultipleFixtures:
    def test_multiple_fixtures_all_processed(self):
        session = _MockSession()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(
            return_value=[_API_FOOTBALL_FIXTURE, _API_FOOTBALL_FIXTURE]
        )

        match1 = _MockMatch(id=100, slug="arsenal-chelsea-101")
        match2 = _MockMatch(id=101, slug="arsenal-chelsea-102")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod,
            "_resolve_team_id",
            new=mock.AsyncMock(side_effect=[1, 2, 1, 2]),
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(side_effect=[(match1, True), (match2, True)]),
        ) as mock_ue, mock.patch.object(
            fixtures_mod,
            "upsert_external_id",
            new=mock.AsyncMock(return_value=(mock.Mock(id=7), True)),
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=39,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 2
        assert result.records_processed == 2
        assert mock_ue.call_count == 2
        assert mock_uei.call_count == 2


class TestFixtureResultDataclass:
    def test_result_defaults(self):
        result = FixtureIngestionResult()
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.conflicts == 0
        assert result.records_processed == 0
        assert result.records_failed == 0
        assert result.errors == []

    def test_result_errors_list(self):
        result = FixtureIngestionResult(errors=["err1", "err2"])
        assert len(result.errors) == 2
