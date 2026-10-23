"""Ingestion job tracking foundation.

Records ingestion job attempts and outcomes in the import_jobs table.
All functions accept an existing AsyncSession and do not commit — the
caller owns transaction boundaries so job tracking can be grouped with
entity upserts in a single transaction.

Job tracking is independent of any particular provider or dataset.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


# ─── Status values ──────────────────────────────────────────────────────
# The import_jobs.status column is String(20) with no CHECK constraint,
# so any short string works. These constants keep callers consistent.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


# ─── Job lifecycle functions ───────────────────────────────────────────


async def create_job(
    session: AsyncSession,
    entity_type: str,
    data_source_id: int,
) -> Any:
    """Create a new ingestion job record with status 'pending'.

    Does not call commit() — the caller owns transaction boundaries.
    The row is flushed so its server-assigned id is available immediately.
    """
    from db.models.import_job import ImportJob

    job = ImportJob(
        entity_type=entity_type,
        data_source_id=data_source_id,
        status=STATUS_PENDING,
    )
    session.add(job)
    await session.flush()
    return job


async def mark_running(session: AsyncSession, job: Any) -> None:
    """Transition a job to 'running' status and refresh started_at."""
    job.status = STATUS_RUNNING
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()


async def complete_job(
    session: AsyncSession,
    job: Any,
    records_processed: int = 0,
    records_failed: int = 0,
) -> None:
    """Mark a job as successfully completed."""
    job.status = STATUS_COMPLETED
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    job.records_processed = records_processed
    job.records_failed = records_failed
    job.error_message = None
    await session.flush()


async def fail_job(
    session: AsyncSession,
    job: Any,
    error_message: str,
    records_processed: int = 0,
    records_failed: int = 0,
) -> None:
    """Mark a job as failed, preserving the error message.

    The error message is truncated to fit the Text column (no DB-level
    length limit, but callers should keep messages bounded).
    """
    job.status = STATUS_FAILED
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    job.records_processed = records_processed
    job.records_failed = records_failed
    job.error_message = error_message if error_message else None
    await session.flush()


# ─── Context manager ───────────────────────────────────────────────────


@asynccontextmanager
async def track_job(
    session: AsyncSession,
    entity_type: str,
    data_source_id: int,
):
    """Context manager that creates a job and auto-completes or auto-fails it.

    Usage:
        async with track_job(session, "team", data_source_id) as job:
            ... ingestion work ...
            job.records_processed = count

    On success the job is marked completed. On exception the job is marked
    failed with the exception message, and the exception is re-raised so the
    caller can decide whether to roll back the enclosing transaction.
    """
    job = await create_job(session, entity_type, data_source_id)
    try:
        yield job
        await complete_job(
            session,
            job,
            records_processed=getattr(job, "records_processed", 0),
            records_failed=getattr(job, "records_failed", 0),
        )
    except Exception as exc:  # noqa: BLE001 — preserve and re-raise
        await fail_job(
            session,
            job,
            str(exc),
            records_processed=getattr(job, "records_processed", 0),
            records_failed=getattr(job, "records_failed", 0),
        )
        raise
