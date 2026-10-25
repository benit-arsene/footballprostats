"""Focused tests for backend/ingestion/fixtures.py fixture ingestion workflow.

All tests use mocked AsyncSession, mocked providers, and mocked registry —
no database, no external APIs.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, time
from unittest import mock

import pytest

import ingestion.fixtures as fixtures_mod
from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.season import Season
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


class _ScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return _ScalarResult(self._rows)

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


def _filter(rows, stmt):
    """Apply the equality predicates a real database would apply."""
    criteria = {}
    for key, value in stmt.compile().params.items():
        name = key.rsplit("_", 1)[0]
        if name == "param":  # LIMIT
            continue
        criteria[name] = value

    selected = []
    for row in rows:
        if all(
            not hasattr(row, name) or getattr(row, name) == value
            for name, value in criteria.items()
        ):
            selected.append(row)
    return selected


class _MockSession:
    """Minimal AsyncSession stand-in for competition/season/external-id reads.

    No database connection is opened. Rows are filtered by the equality
    predicates of each query so id handling is actually exercised.
    """

    def __init__(
        self,
        competition=None,
        season=None,
        competition_mappings=(),
        match_mapping=None,
        matches=(),
    ):
        self.competition = competition
        self.season = season
        self.competition_mappings = list(competition_mappings)
        self.match_mapping = match_mapping
        self.matches = list(matches)
        self.added = []
        self.flushed = 0
        self.savepoint_commits = 0
        self.savepoint_rollbacks = 0

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        self.flushed += 1

    @asynccontextmanager
    async def begin_nested(self):
        snapshot = len(self.added)
        flushed = self.flushed
        try:
            yield
        except Exception:
            # Roll back partial writes to the savepoint.
            del self.added[snapshot:]
            self.flushed = flushed
            self.savepoint_rollbacks = getattr(self, "savepoint_rollbacks", 0) + 1
            raise
        else:
            self.savepoint_commits = getattr(self, "savepoint_commits", 0) + 1

    def __init__(
        self,
        competition=None,
        season=None,
        competition_mappings=(),
        match_mapping=None,
        matches=(),
    ):
        self.competition = competition
        self.season = season
        self.competition_mappings = list(competition_mappings)
        self.match_mapping = match_mapping
        self.matches = list(matches)
        self.added = []
        self.flushed = 0

    async def execute(self, stmt):
        sql = str(stmt)
        if "FROM competitions" in sql:
            rows = [self.competition] if self.competition is not None else []
        elif "FROM seasons" in sql:
            rows = [self.season] if self.season is not None else []
        elif "FROM matches" in sql:
            rows = list(self.matches)
        elif "FROM external_ids" in sql:
            rows = list(self.competition_mappings)
            if self.match_mapping is not None:
                rows.append(self.match_mapping)
        else:
            raise AssertionError(f"unexpected query in test: {sql}")
        return _Result(_filter(rows, stmt))


def _stored_session(
    *,
    competition_id=1,
    season_id=5,
    provider="api_football",
    external_id="39",
    season_competition_id=None,
    season_label="2026/2027",
    season_start=None,
    extra_mappings=(),
    match_mapping=None,
):
    """Session containing the internal rows and external-id mappings."""
    competition = Competition(
        id=competition_id,
        name=f"Competition {competition_id}",
        slug=f"competition-{competition_id}",
    )
    season = Season(
        id=season_id,
        competition_id=(
            season_competition_id if season_competition_id is not None else competition_id
        ),
        label=season_label,
        start_date=season_start,
    )
    mappings = [
        ExternalId(
            id=1,
            entity_type="competition",
            provider=provider,
            external_id=external_id,
            competition_id=competition_id,
        ),
        *extra_mappings,
    ]
    return _MockSession(
        competition=competition,
        season=season,
        competition_mappings=mappings,
        match_mapping=match_mapping,
    )


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
        session = _stored_session()

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
                    competition_id=1,
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
        assert mock_job.records_processed == 1
        assert mock_job.records_failed == 0
        assert provider_mock.get_fixtures.await_count == 1
        # The provider receives its own league id, resolved from external_ids.
        call_kwargs = provider_mock.get_fixtures.await_args.kwargs
        assert call_kwargs["league_id"] == 39
        assert call_kwargs["season"] == 2026

        # Verify upsert_entity called with correct Match fields
        ue_call = mock_ue.call_args
        assert ue_call.kwargs["conflict_keys"] == {"slug": "arsenal-vs-chelsea-101"}
        assert ue_call.kwargs["values"]["competition_id"] == 1
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
        session = _stored_session()

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
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 0
        assert result.updated == 1
        assert result.records_processed == 1
        assert mock_job.records_processed == 1
        assert mock_job.records_failed == 0
        assert mock_ue.call_args.kwargs["conflict_keys"] == {"slug": "arsenal-vs-chelsea-101"}


class TestExternalIdMapping:
    def test_mapping_connects_provider_id_to_internal_id(self):
        session = _stored_session()

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
                    competition_id=1,
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
        session = _stored_session()

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
                    competition_id=1,
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
        session = _stored_session()
        session.match_mapping = ExternalId(
            id=9,
            entity_type="match",
            provider="api_football",
            external_id="101",
            match_id=999,
        )
        # A row with the provider's slug already exists under a *different*
        # internal id, so the conflict must be caught before any upsert.
        session.matches = [_MockMatch(id=200, slug="arsenal-vs-chelsea-101")]

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        new_match = _MockMatch(id=200, slug="arsenal-vs-chelsea-101")

        # Conflict detection: external_id "101" already maps to match_id 999.

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
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.conflicts == 1
        assert result.records_failed == 1
        assert result.records_processed == 0
        # The conflict must prevent the Match from being inserted or updated,
        # not merely prevent the external-id row from being written.
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()
        assert session.added == []
        assert mock_job.records_failed == 1
        assert mock_job.records_processed == 0
        assert "already maps to match_id 999" in result.errors[0]

    def test_conflict_without_existing_match_row_skips_upsert(self):
        """A dangling conflicting mapping still must not create a Match."""
        session = _stored_session()
        session.match_mapping = ExternalId(
            id=9,
            entity_type="match",
            provider="api_football",
            external_id="101",
            match_id=999,
        )

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod, "_resolve_team_id", new=mock.AsyncMock(side_effect=[1, 2])
        ), mock.patch.object(
            fixtures_mod, "upsert_entity", new=mock.AsyncMock()
        ) as mock_ue, mock.patch.object(
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.conflicts == 1
        assert result.records_failed == 1
        assert result.records_processed == 0
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()
        assert session.added == []

    def test_mapping_to_same_match_remains_idempotent(self):
        """An existing correct mapping is reused and not rewritten."""
        session = _stored_session()
        existing_match = _MockMatch(id=100, slug="arsenal-vs-chelsea-101")
        session.matches = [existing_match]
        session.match_mapping = ExternalId(
            id=9,
            entity_type="match",
            provider="api_football",
            external_id="101",
            match_id=100,
        )

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(return_value=[_API_FOOTBALL_FIXTURE])

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
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.updated == 1
        assert result.records_processed == 1
        assert result.records_failed == 0
        assert result.conflicts == 0
        mock_ue.assert_called_once()
        mock_uei.assert_not_called()
        assert mock_job.records_processed == 1
        assert mock_job.records_failed == 0


class TestMixedOutcomes:
    def test_success_failure_and_skip_counts(self):
        """Job and result counters stay aligned across mixed outcomes."""
        session = _stored_session()

        provider_mock = mock.Mock()
        provider_mock.get_fixtures = mock.AsyncMock(
            return_value=[
                _API_FOOTBALL_FIXTURE,
                _API_FOOTBALL_FIXTURE,
                _API_FOOTBALL_FIXTURE,
            ]
        )

        match_mock = _MockMatch(id=100, slug="arsenal-vs-chelsea-101")

        with _mock_registry("api_football", provider_mock), _mock_track_job() as (
            track_patcher,
            mock_job,
        ), mock.patch.object(
            fixtures_mod,
            "_resolve_team_id",
            new=mock.AsyncMock(
                side_effect=[1, 2, RuntimeError("team lookup exploded"), None, None]
            ),
        ), mock.patch.object(
            fixtures_mod,
            "upsert_entity",
            new=mock.AsyncMock(return_value=(match_mock, True)),
        ) as mock_ue, mock.patch.object(
            fixtures_mod, "upsert_external_id", new=mock.AsyncMock()
        ) as mock_uei:
            track_patcher.start()
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name="api_football",
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        # 1 created, 1 failed (unexpected processing error), 1 skipped fixture.
        assert result.created == 1
        assert result.skipped == 1
        assert result.records_processed == 1
        assert result.records_failed == 1
        assert result.conflicts == 0
        assert len(result.errors) == 1
        assert "team lookup exploded" in result.errors[0]
        assert mock_ue.call_count == 1
        assert mock_uei.call_count == 1
        # Persisted job counters mirror the returned result exactly.
        assert mock_job.records_processed == result.records_processed
        assert mock_job.records_failed == result.records_failed


class TestEmptyResponse:
    def test_empty_provider_response(self):
        session = _stored_session()

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
                    competition_id=1,
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
        assert mock_job.records_processed == 0
        assert mock_job.records_failed == 0
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()


class TestProviderError:
    def test_provider_error_re_raised(self):
        session = _stored_session()

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
                        competition_id=1,
                        season_id=5,
                        data_source_id=1,
                        season_year=2026,
                    )
                )


class TestMissingTeamMapping:
    def test_fixture_skipped_when_team_not_mapped(self):
        session = _stored_session()

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
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.skipped == 1
        assert result.created == 0
        assert result.updated == 0
        # Skipped fixtures are neither processed nor failed.
        assert result.records_processed == 0
        assert result.records_failed == 0
        assert mock_job.records_processed == 0
        assert mock_job.records_failed == 0
        mock_ue.assert_not_called()
        mock_uei.assert_not_called()


class TestUnknownProvider:
    def test_unknown_provider_raises_value_error(self):
        session = _stored_session()

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
                        competition_id=1,
                        season_id=5,
                        data_source_id=1,
                        season_year=2026,
                    )
                )


class TestCompetitionSeasonFK:
    def test_competition_and_season_ids_preserved(self):
        session = _stored_session(
            competition_id=2, season_id=12, external_id="140"
        )

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
                    competition_id=2,
                    season_id=12,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        # Internal IDs are stored as FK values …
        ue_call = mock_ue.call_args
        assert ue_call.kwargs["values"]["competition_id"] == 2
        assert ue_call.kwargs["values"]["season_id"] == 12
        # … while the provider is asked for its own La Liga league id.
        assert provider_mock.get_fixtures.await_args.kwargs["league_id"] == 140


class TestFootballDataFormat:
    def test_football_data_fixture_normalized(self):
        session = _stored_session(provider="football_data", external_id="PL")

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
                    competition_id=1,
                    season_id=5,
                    data_source_id=2,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 1
        assert result.records_processed == 1
        assert mock_job.records_processed == 1
        assert mock_job.records_failed == 0
        # Stored football-data.org code "PL" is passed as that provider's own
        # competition reference, never the internal id or API-Football's 39.
        call_kwargs = provider_mock.get_fixtures.await_args.kwargs
        assert call_kwargs["league_id"] == "PL"
        assert call_kwargs["season"] == 2026
        ue_call = mock_ue.call_args
        assert ue_call.kwargs["values"]["competition_id"] == 1
        assert ue_call.kwargs["values"]["season_id"] == 5
        # External ID mapping uses football-data provider name
        uei_call = mock_uei.call_args
        assert uei_call.kwargs["provider"] == "football_data"
        assert uei_call.kwargs["external_id"] == "201"


class TestMultipleFixtures:
    def test_multiple_fixtures_all_processed(self):
        session = _stored_session()

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
                    competition_id=1,
                    season_id=5,
                    data_source_id=1,
                    season_year=2026,
                )
            )
            track_patcher.stop()

        assert result.created == 2
        assert result.records_processed == 2
        assert mock_job.records_processed == 2
        assert mock_job.records_failed == 0
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


# ─── Competition / season provider-ID resolution ────────────────────────


def _provider_mock(provider_name: str = "api_football"):
    provider = mock.Mock()
    payload = (
        [_API_FOOTBALL_FIXTURE]
        if provider_name == "api_football"
        else [_FOOTBALL_DATA_FIXTURE]
    )
    provider.get_fixtures = mock.AsyncMock(return_value=payload)
    return provider


def _run_ingest(
    session,
    provider_mock,
    *,
    provider_name: str = "api_football",
    competition_id: int = 1,
    season_id: int = 5,
    season_year: int | None = None,
):
    """Run ingest_fixtures with the external boundaries mocked."""
    match_mock = _MockMatch(id=100, slug="arsenal-chelsea-101")

    with _mock_registry(provider_name, provider_mock), _mock_track_job() as (
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
        try:
            result = _run_async(
                ingest_fixtures(
                    session,
                    provider_name=provider_name,
                    competition_id=competition_id,
                    season_id=season_id,
                    data_source_id=1,
                    season_year=season_year,
                )
            )
        finally:
            track_patcher.stop()

    return result, mock_ue, mock_uei


class TestProviderCompetitionResolution:
    def test_internal_competition_resolves_to_provider_league_id(self):
        """Internal PK 7 is never sent to the provider; its mapping (39) is."""
        session = _stored_session(competition_id=7, external_id="39")
        provider = _provider_mock()

        result, mock_ue, mock_uei = _run_ingest(
            session, provider, competition_id=7
        )

        assert result.created == 1
        assert provider.get_fixtures.await_args.kwargs["league_id"] == 39
        values = mock_ue.call_args.kwargs["values"]
        assert values["competition_id"] == 7
        assert values["season_id"] == 5
        # Provider match IDs stay in external_ids, mapped to the internal match.
        mapping = mock_uei.call_args.kwargs
        assert mapping["provider"] == "api_football"
        assert mapping["external_id"] == "101"
        assert mapping["internal_id"] == 100
        assert mapping["entity_column"] == "match_id"

    def test_provider_request_does_not_use_internal_id(self):
        session = _stored_session(competition_id=1, external_id="39")
        provider = _provider_mock()

        _run_ingest(session, provider, competition_id=1)

        assert provider.get_fixtures.await_args.kwargs["league_id"] != 1

    def test_football_data_receives_its_own_competition_code(self):
        session = _stored_session(provider="football_data", external_id="PD")
        provider = _provider_mock("football_data")

        _, mock_ue, mock_uei = _run_ingest(
            session, provider, provider_name="football_data"
        )

        # "PD" is football-data.org's own competition code. The internal id
        # (1) and API-Football's id for La Liga (140) are never sent.
        league_id = provider.get_fixtures.await_args.kwargs["league_id"]
        assert league_id == "PD"
        assert mock_ue.call_args.kwargs["values"]["competition_id"] == 1
        assert mock_uei.call_args.kwargs["provider"] == "football_data"
        assert mock_uei.call_args.kwargs["external_id"] == "201"

    def test_missing_mapping_prevents_provider_call(self):
        session = _stored_session()
        session.competition_mappings = []
        provider = _provider_mock()

        with pytest.raises(ValueError, match="No api_football competition mapping"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0
        assert session.added == []

    def test_mapping_from_another_provider_is_not_used(self):
        session = _stored_session(provider="football_data", external_id="PL")
        provider = _provider_mock("api_football")

        with pytest.raises(ValueError, match="No api_football competition mapping"):
            _run_ingest(session, provider, provider_name="api_football")

        assert provider.get_fixtures.await_count == 0

    def test_ambiguous_mapping_prevents_provider_call(self):
        session = _stored_session(external_id="39")
        session.competition_mappings.append(
            ExternalId(
                id=2,
                entity_type="competition",
                provider="api_football",
                external_id="40",
                competition_id=1,
            )
        )
        provider = _provider_mock()

        with pytest.raises(ValueError, match="Ambiguous api_football competition mapping"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0

    def test_non_numeric_api_football_mapping_is_rejected(self):
        session = _stored_session(external_id="PL")
        provider = _provider_mock()

        with pytest.raises(ValueError, match="not a numeric provider league id"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0

    def test_football_data_mapping_must_be_a_competition_code(self):
        session = _stored_session(provider="football_data", external_id="2021")
        provider = _provider_mock("football_data")

        with pytest.raises(ValueError, match="not a supported competition code"):
            _run_ingest(session, provider, provider_name="football_data")

        assert provider.get_fixtures.await_count == 0

    def test_missing_competition_prevents_provider_call(self):
        session = _stored_session()
        session.competition = None
        provider = _provider_mock()

        with pytest.raises(ValueError, match="Competition 1 not found"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0

    def test_missing_season_prevents_provider_call(self):
        session = _stored_session()
        session.season = None
        provider = _provider_mock()

        with pytest.raises(ValueError, match="Season 5 not found"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0

    def test_season_from_another_competition_is_rejected(self):
        session = _stored_session(competition_id=1, season_competition_id=2)
        provider = _provider_mock()

        with pytest.raises(ValueError, match="belongs to competition 2"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0


class TestProviderSeasonResolution:
    def test_season_year_derived_from_stored_label(self):
        session = _stored_session(season_label="2025/2026")
        provider = _provider_mock()

        _run_ingest(session, provider, season_year=None)

        assert provider.get_fixtures.await_args.kwargs["season"] == 2025

    def test_season_year_derived_from_stored_start_date(self):
        session = _stored_session(
            season_label="2024/2025",
            season_start=datetime(2024, 8, 16, 0, 0),
        )
        provider = _provider_mock()

        _run_ingest(session, provider, season_year=None)

        assert provider.get_fixtures.await_args.kwargs["season"] == 2024

    def test_matching_season_year_is_accepted(self):
        session = _stored_session(season_label="2026/2027")
        provider = _provider_mock()

        _run_ingest(session, provider, season_year=2026)

        assert provider.get_fixtures.await_args.kwargs["season"] == 2026

    def test_conflicting_season_year_prevents_provider_call(self):
        session = _stored_session(season_label="2026/2027")
        provider = _provider_mock()

        with pytest.raises(ValueError, match="does not match stored season"):
            _run_ingest(session, provider, season_year=2025)

        assert provider.get_fixtures.await_count == 0

    def test_season_without_usable_year_is_rejected(self):
        session = _stored_session(season_label="unknown", season_start=None)
        provider = _provider_mock()

        with pytest.raises(ValueError, match="no usable start date or label"):
            _run_ingest(session, provider)

        assert provider.get_fixtures.await_count == 0
