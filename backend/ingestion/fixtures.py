"""Fixture ingestion workflow.

Builds on:
  backend/ingestion/service.py   — upsert_entity, upsert_external_id
  backend/ingestion/jobs.py      — track_job context manager

Responsibilities:
  1. Accept provider, competition, season parameters
  2. Fetch fixtures from the selected provider
  3. Normalize using existing adapters (normalization/matches.py)
  4. Upsert Match rows via slug (verified unique constraint)
  5. Create external_ids mappings via match_id column
  6. Track job outcomes via track_job context manager
  7. Preserve existing values on optional field absence
  8. Detect and report external-ID mapping conflicts

No provider JSON parsing or normalization happens here — that lives in
normalization/matches.py and the provider adapters. No commit() is called;
the caller owns transaction boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.external_id import ExternalId
from db.models.match import Match
from ingestion.jobs import track_job
from ingestion.service import upsert_entity, upsert_external_id
from normalization.matches import normalize_match_summary
from providers.factory import build_provider_registry

logger = logging.getLogger("ingestion.fixtures")


@dataclass
class FixtureIngestionResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: int = 0
    records_processed: int = 0
    records_failed: int = 0
    errors: list[str] = field(default_factory=list)


# ─── Internal helpers ───────────────────────────────────────────────────


async def _resolve_team_id(
    session: AsyncSession,
    provider_name: str,
    external_id: int | str | None,
) -> int | None:
    """Look up internal team ID from the external_ids mapping.

    Returns None when no mapping exists or the mapping has no team_id set.
    """
    if external_id is None:
        return None
    result = await session.execute(
        select(ExternalId).where(
            ExternalId.entity_type == "team",
            ExternalId.provider == provider_name,
            ExternalId.external_id == str(external_id),
        )
    )
    ext = result.scalar_one_or_none()
    if ext is None or ext.team_id is None:
        return None
    return ext.team_id


def _parse_date(date_str: str | None) -> date | None:
    """Parse a YYYY-MM-DD string into a date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None


def _parse_time(time_str: str | None) -> time | None:
    """Parse a HH:MM string into a time object."""
    if not time_str:
        return None
    try:
        parts = str(time_str).split(":")
        return time(hour=int(parts[0]), minute=int(parts[1]))
    except (ValueError, TypeError, IndexError):
        return None


def _status_str(status: Any) -> str:
    """Convert a MatchStatus enum or string to a plain string."""
    if hasattr(status, "value"):
        return status.value
    return str(status)


# ─── Public API ─────────────────────────────────────────────────────────


async def ingest_fixtures(
    session: AsyncSession,
    provider_name: str,
    competition_id: int,
    season_id: int,
    data_source_id: int,
    season_year: int | None = None,
) -> FixtureIngestionResult:
    """Ingest fixtures for a competition/season from a specific provider.

    Args:
        session: Open AsyncSession (caller owns commit/rollback).
        provider_name: Provider name, e.g. "api_football" or "football_data".
        competition_id: Internal competition PK (used as provider league_id).
        season_id: Internal season PK (for Match.season_id FK).
        data_source_id: DataSource PK for job tracking.
        season_year: Provider season year (e.g. 2026). Passed to the provider.

    Returns:
        FixtureIngestionResult with counts of created/updated/skipped/
        conflicts/records_processed/records_failed and any error messages.

    Raises:
        ValueError: If the provider is not registered.
    """
    registry = build_provider_registry()
    if not registry.has_provider(provider_name):
        raise ValueError(f"Unknown provider: {provider_name}")
    provider = registry.get_provider(provider_name)

    result = FixtureIngestionResult()

    async with track_job(session, "match", data_source_id) as job:
        try:
            fixtures_raw = await provider.get_fixtures(
                league_id=competition_id,
                season=season_year,
            )
        except Exception:
            # Provider failure — track_job marks the job failed and re-raises.
            raise

        if not fixtures_raw:
            return result

        for raw in fixtures_raw:
            try:
                # Normalize via existing adapter layer — no provider JSON
                # parsing or normalization logic duplicated here.
                summary = normalize_match_summary(raw)

                # Resolve internal team IDs via external_ids mapping.
                home_internal = await _resolve_team_id(
                    session, provider_name, summary.home_team.id
                )
                away_internal = await _resolve_team_id(
                    session, provider_name, summary.away_team.id
                )

                if home_internal is None or away_internal is None:
                    result.skipped += 1
                    continue

                # Parse temporal fields from canonical model strings.
                match_date = _parse_date(summary.date)
                if match_date is None:
                    result.skipped += 1
                    continue
                kickoff = _parse_time(summary.kickoff_time)

                # Upsert Match row — conflict key is slug (unique constraint).
                match, match_created = await upsert_entity(
                    session,
                    Match,
                    conflict_keys={"slug": summary.slug},
                    values={
                        "competition_id": competition_id,
                        "season_id": season_id,
                        "home_team_id": home_internal,
                        "away_team_id": away_internal,
                        "date": match_date,
                        "kickoff_time": kickoff,
                        "status": _status_str(summary.status),
                        "minute": summary.minute,
                        "home_score": summary.home_score,
                        "away_score": summary.away_score,
                    },
                    preserve_existing=True,
                )

                if match_created:
                    result.created += 1
                else:
                    result.updated += 1

                # Create/update external_ids mapping for this match.
                ext_id = str(summary.id)

                # Conflict detection: does this external_id already map to a
                # different internal match ID?
                stmt = select(ExternalId).where(
                    ExternalId.entity_type == "match",
                    ExternalId.provider == provider_name,
                    ExternalId.external_id == ext_id,
                )
                ext_result = await session.execute(stmt)
                existing_ext = ext_result.scalar_one_or_none()

                if existing_ext is not None:
                    existing_match_id = getattr(existing_ext, "match_id", None)
                    if existing_match_id is not None and existing_match_id != match.id:
                        # CONFLICT: same provider+external_id maps to a
                        # different internal match. Do not reassign.
                        result.conflicts += 1
                        result.records_failed += 1
                        result.errors.append(
                            f"external_id {ext_id} ({provider_name}) already "
                            f"maps to match_id {existing_match_id}, not {match.id}"
                        )
                        continue
                    # Already maps to the same match — no action needed.

                # Upsert external_ids mapping via match_id column.
                await upsert_external_id(
                    session,
                    entity_type="match",
                    provider=provider_name,
                    external_id=ext_id,
                    internal_id=match.id,
                    entity_column="match_id",
                )

                result.records_processed += 1

            except Exception as exc:  # noqa: BLE001 — record and continue batch
                result.records_failed += 1
                result.errors.append(str(exc))
                logger.warning(
                    "Fixture ingestion failed for id=%s: %s",
                    raw.get("id", "unknown") if isinstance(raw, dict) else "unknown",
                    exc,
                )

    return result
