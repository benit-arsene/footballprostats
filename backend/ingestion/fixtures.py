"""Fixture ingestion workflow.

Builds on:
  backend/ingestion/service.py   — upsert_entity, upsert_external_id
  backend/ingestion/jobs.py      — track_job context manager

Responsibilities:
  1. Accept provider, competition, season parameters
  2. Resolve internal competition/season rows to provider-specific identifiers
  3. Fetch fixtures from the selected provider
  4. Normalize using existing adapters (normalization/matches.py)
  5. Upsert Match rows via slug (verified unique constraint)
  6. Create external_ids mappings via match_id column
  7. Track job outcomes via track_job context manager
  8. Preserve existing values on optional field absence
  9. Detect and report external-ID mapping conflicts

ID boundary: ``competition_id`` and ``season_id`` are internal primary keys and
remain the foreign keys written to ``matches``. Provider identifiers are
resolved from ``external_ids`` (competition) and the stored season row, and are
only ever sent to the provider. No provider is called when a mapping is
missing, ambiguous, or belongs to another provider.

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

from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.match import Match
from db.models.season import Season
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


# ─── Provider-specific ID resolution ────────────────────────────────────


def _season_start_year(season: Season) -> int:
    """Provider season year for a stored season.

    Both supported providers take the season's start year as an integer, so the
    value is derived from the stored season (start date first, then the
    ``YYYY/YYYY`` label). It is never taken from an internal ``seasons.id``.
    """
    if season.start_date is not None:
        return season.start_date.year

    label = (season.label or "").strip()
    first = label.split("/", 1)[0]
    try:
        return int(first)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Season {season.id} has no usable start date or label "
            f"(label={season.label!r}); cannot resolve the provider season"
        ) from exc


def _provider_competition_reference(
    provider_name: str, external_id: str
) -> int | str:
    """Translate a stored competition mapping into the provider's own reference.

    API-Football takes its own numeric league id (for example ``39``).
    football-data.org takes its own competition code (``PL``). Each provider
    receives the value from its own mapping row; an id from another provider's
    namespace is never passed through.
    """
    if provider_name == "api_football":
        try:
            return int(external_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"API-Football competition mapping {external_id!r} is not a "
                "numeric provider league id"
            ) from exc

    if provider_name == "football_data":
        from providers.football_data.adapters import CODE_TO_COMPETITION_ID

        code = str(external_id).strip().upper()
        if code not in CODE_TO_COMPETITION_ID:
            raise ValueError(
                f"football-data.org competition mapping {external_id!r} is not a "
                "supported competition code (expected one of "
                f"{sorted(CODE_TO_COMPETITION_ID)})"
            )
        return code

    raise ValueError(f"Unsupported provider for competition resolution: {provider_name}")


async def _resolve_provider_competition_id(
    session: AsyncSession,
    provider_name: str,
    competition_id: int,
) -> int | str:
    """Resolve an internal competition PK to the selected provider's id.

    Only mappings recorded for the same provider are considered — a row from a
    different provider is never used as a fallback. A missing or ambiguous
    mapping raises instead of guessing.
    """
    result = await session.execute(
        select(ExternalId).where(
            ExternalId.entity_type == "competition",
            ExternalId.provider == provider_name,
            ExternalId.competition_id == competition_id,
        )
    )
    external_ids = {
        str(row.external_id)
        for row in result.scalars().all()
        if row.external_id is not None and str(row.external_id).strip()
    }

    if not external_ids:
        raise ValueError(
            f"No {provider_name} competition mapping for internal competition "
            f"{competition_id}; refusing to fetch fixtures"
        )
    if len(external_ids) > 1:
        raise ValueError(
            f"Ambiguous {provider_name} competition mapping for internal "
            f"competition {competition_id}: {sorted(external_ids)}"
        )

    return _provider_competition_reference(provider_name, external_ids.pop())


async def _resolve_competition_and_season(
    session: AsyncSession,
    competition_id: int,
    season_id: int,
) -> tuple[Competition, Season]:
    """Load the internal competition/season rows and verify they belong together."""
    competition_result = await session.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = competition_result.scalar_one_or_none()
    if competition is None:
        raise ValueError(f"Competition {competition_id} not found")

    season_result = await session.execute(
        select(Season).where(Season.id == season_id)
    )
    season = season_result.scalar_one_or_none()
    if season is None:
        raise ValueError(f"Season {season_id} not found")
    if season.competition_id != competition.id:
        raise ValueError(
            f"Season {season_id} belongs to competition {season.competition_id}, "
            f"not competition {competition.id}"
        )

    return competition, season


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
        competition_id: Internal competition PK (stored on Match.competition_id).
        season_id: Internal season PK (stored on Match.season_id).
        data_source_id: DataSource PK for job tracking.
        season_year: Optional provider season year used as a consistency check.
            The value sent to the provider always comes from the stored season;
            a mismatch raises instead of fetching a different season.

    Returns:
        FixtureIngestionResult with counts of created/updated/skipped/
        conflicts/records_processed/records_failed and any error messages.

    Raises:
        ValueError: If the provider is not registered, the competition/season
            rows are missing or inconsistent, or the provider competition
            mapping is missing, ambiguous, or in the wrong provider's id space.
            In those cases no provider request is made and nothing is written.
    """
    registry = build_provider_registry()
    if not registry.has_provider(provider_name):
        raise ValueError(f"Unknown provider: {provider_name}")
    provider = registry.get_provider(provider_name)

    # Resolve provider-specific identifiers before any request is made. The
    # internal PKs stay the foreign keys written to matches.
    _, season = await _resolve_competition_and_season(
        session, competition_id, season_id
    )
    provider_league_id = await _resolve_provider_competition_id(
        session, provider_name, competition_id
    )
    provider_season_year = _season_start_year(season)
    if season_year is not None and int(season_year) != provider_season_year:
        raise ValueError(
            f"Requested season year {season_year} does not match stored season "
            f"{season.label!r} ({provider_season_year})"
        )

    result = FixtureIngestionResult()

    async with track_job(session, "match", data_source_id) as job:
        try:
            fixtures_raw = await provider.get_fixtures(
                league_id=provider_league_id,
                season=provider_season_year,
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
