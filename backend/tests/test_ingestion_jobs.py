"""Focused tests for backend/ingestion/jobs.py job tracking foundation.

All tests use mocked AsyncSession — no database, no external APIs.
"""

import asyncio
from datetime import datetime
from unittest import mock

import pytest

import ingestion.jobs as jobs_mod
from ingestion.jobs import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    complete_job,
    create_job,
    fail_job,
    mark_running,
    track_job,
)


# ─── Mock helpers ───────────────────────────────────────────────────────


class _MockSession:
    """SQLAlchemy 2.0 AsyncSession stand-in: add() is sync, flush awaited."""

    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        self.flushed += 1


class _MockJob:
    """Stand-in for an ImportJob model instance."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _run_async(coro):
    return asyncio.run(coro)


# ─── create_job tests ───────────────────────────────────────────────────


class TestCreateJob:
    def test_create_job_pending_status(self):
        session = _MockSession()

        job = _run_async(create_job(session, entity_type="team", data_source_id=1))

        assert len(session.added) == 1
        assert session.flushed == 1
        assert job.entity_type == "team"
        assert job.data_source_id == 1
        assert job.status == STATUS_PENDING

    def test_create_job_different_entity_types(self):
        session = _MockSession()

        _run_async(create_job(session, entity_type="competition", data_source_id=2))
        _run_async(create_job(session, entity_type="match", data_source_id=3))

        assert len(session.added) == 2
        assert session.added[0].entity_type == "competition"
        assert session.added[1].entity_type == "match"


# ─── mark_running tests ─────────────────────────────────────────────────


class TestMarkRunning:
    def test_mark_running_sets_status_and_timestamp(self):
        session = _MockSession()
        job = _MockJob(status=STATUS_PENDING, started_at=datetime(2026, 1, 1))

        _run_async(mark_running(session, job))

        assert job.status == STATUS_RUNNING
        assert session.flushed == 1
        assert isinstance(job.started_at, datetime)


# ─── complete_job tests ─────────────────────────────────────────────────


class TestCompleteJob:
    def test_complete_job_sets_completed_status(self):
        session = _MockSession()
        job = _MockJob(
            status=STATUS_RUNNING,
            completed_at=None,
            records_processed=0,
            records_failed=0,
            error_message="some old error",
        )

        _run_async(
            complete_job(session, job, records_processed=10, records_failed=0)
        )

        assert job.status == STATUS_COMPLETED
        assert job.completed_at is not None
        assert isinstance(job.completed_at, datetime)
        assert job.records_processed == 10
        assert job.records_failed == 0
        assert job.error_message is None
        assert session.flushed == 1

    def test_complete_job_clears_error_message(self):
        session = _MockSession()
        job = _MockJob(status=STATUS_FAILED, error_message="previous failure")

        _run_async(complete_job(session, job, records_processed=5))

        assert job.status == STATUS_COMPLETED
        assert job.error_message is None


# ─── fail_job tests ─────────────────────────────────────────────────────


class TestFailJob:
    def test_fail_job_sets_failed_status_and_message(self):
        session = _MockSession()
        job = _MockJob(
            status=STATUS_RUNNING,
            completed_at=None,
            records_processed=3,
            records_failed=2,
            error_message=None,
        )

        _run_async(
            fail_job(session, job, "connection timeout", records_processed=3, records_failed=2)
        )

        assert job.status == STATUS_FAILED
        assert job.completed_at is not None
        assert isinstance(job.completed_at, datetime)
        assert job.records_processed == 3
        assert job.records_failed == 2
        assert job.error_message == "connection timeout"
        assert session.flushed == 1

    def test_fail_job_empty_message(self):
        session = _MockSession()
        job = _MockJob(status=STATUS_RUNNING)

        _run_async(fail_job(session, job, ""))

        assert job.status == STATUS_FAILED
        assert job.error_message is None


# ─── track_job context manager tests ────────────────────────────────────


class TestTrackJob:
    async def _run_track_job_success(self, session):
        with mock.patch.object(jobs_mod, "create_job", new=mock.AsyncMock()) as mock_create:
            mock_job = _MockJob(status=STATUS_PENDING, records_processed=0, records_failed=0)
            mock_create.return_value = mock_job
            with mock.patch.object(jobs_mod, "complete_job", new=mock.AsyncMock()) as mock_complete:
                mock_complete.return_value = None
                async with track_job(session, entity_type="season", data_source_id=1) as job:
                    assert job is mock_job
                    job.records_processed = 7

        mock_create.assert_called_once_with(session, "season", 1)
        mock_complete.assert_called_once()
        call_args = mock_complete.call_args
        assert call_args.args[1] is mock_job  # job is 2nd positional arg
        assert call_args.kwargs["records_processed"] == 7

    def test_track_job_success_completes(self):
        session = _MockSession()
        _run_async(self._run_track_job_success(session))

    async def _run_track_job_failure(self, session):
        exc = RuntimeError("provider unreachable")
        with mock.patch.object(jobs_mod, "create_job", new=mock.AsyncMock()) as mock_create:
            mock_job = _MockJob(status=STATUS_PENDING, records_processed=0, records_failed=0)
            mock_create.return_value = mock_job
            with mock.patch.object(jobs_mod, "fail_job", new=mock.AsyncMock()) as mock_fail:
                mock_fail.return_value = None
                with pytest.raises(RuntimeError, match="provider unreachable"):
                    async with track_job(session, entity_type="team", data_source_id=1) as job:
                        assert job is mock_job
                        raise exc

        mock_fail.assert_called_once()
        call_args = mock_fail.call_args
        assert call_args.args[1] is mock_job  # job is 2nd positional arg
        assert call_args.args[2] == "provider unreachable"  # error_message is 3rd positional arg

    def test_track_job_failure_fails_and_reraises(self):
        session = _MockSession()
        _run_async(self._run_track_job_failure(session))

    async def _run_track_job_preserves_exception_type(self, session):
        with mock.patch.object(jobs_mod, "create_job", new=mock.AsyncMock()):
            with mock.patch.object(jobs_mod, "fail_job", new=mock.AsyncMock()):
                with pytest.raises(ValueError):
                    async with track_job(session, entity_type="player", data_source_id=1):
                        raise ValueError("bad data")

    def test_track_job_preserves_exception_type(self):
        session = _MockSession()
        _run_async(self._run_track_job_preserves_exception_type(session))


# ─── Status constants ───────────────────────────────────────────────────


class TestStatusConstants:
    def test_status_values_are_short_strings(self):
        for status in (STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED):
            assert isinstance(status, str)
            assert len(status) <= 20
            assert status  # non-empty

    def test_status_values_are_distinct(self):
        values = {STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED}
        assert len(values) == 4
