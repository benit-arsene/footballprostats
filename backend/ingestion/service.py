"""Database-first ingestion upsert foundation.

Provides a small, reusable upsert helper for normalized internal data.
The helper uses verified unique constraints as conflict keys and follows
a lookup-and-update pattern (not session.merge()) so that provider IDs are
never conflated with internal IDs.

Provider JSON parsing and normalization live outside this module. This
module only persists canonical SQLAlchemy model instances.

All functions accept an existing AsyncSession and do not commit — the
caller owns transaction boundaries so multiple entities can be persisted
atomically.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.base import Base


# ─── Generic upsert ──────────────────────────────────────────────────────


async def upsert_entity(
    session: AsyncSession,
    model: type[Base],
    conflict_keys: dict[str, Any],
    values: dict[str, Any],
    preserve_existing: bool = True,
) -> tuple[Base, bool]:
    """Insert or update a single entity by verified conflict keys.

    Args:
        session: Open AsyncSession (caller owns commit/rollback).
        model: SQLAlchemy declarative model class.
        conflict_keys: Column -> value used to locate an existing row.
            Must correspond to a unique constraint/index on the table.
        values: Column -> value to set. Only non-None values are written.
        preserve_existing: When True, an existing column that is already
            non-None is not overwritten by an incoming None. When False,
            incoming None values overwrite existing values.

    Returns:
        (entity, created) where created is True if a new row was inserted.
    """
    stmt = select(model)
    for col_name, col_value in conflict_keys.items():
        stmt = stmt.where(getattr(model, col_name) == col_value)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        for col_name, col_value in values.items():
            if col_value is None:
                if preserve_existing:
                    continue
            setattr(existing, col_name, col_value)
        await session.flush()
        return existing, False

    instance = model(**{**conflict_keys, **values})
    session.add(instance)
    await session.flush()
    return instance, True


# ─── External ID mapping upsert ─────────────────────────────────────────


async def upsert_external_id(
    session: AsyncSession,
    entity_type: str,
    provider: str,
    external_id: str,
    internal_id: int,
    entity_column: str,
) -> tuple[Any, bool]:
    """Create or update an external_ids mapping row.

    Uses the unique constraint (entity_type, provider, external_id) as the
    conflict key. Preserves existing internal_id references — an incoming
    mapping for the same provider+external_id will not overwrite a
    different internal_id unless explicitly allowed.

    Args:
        session: Open AsyncSession.
        entity_type: One of "competition", "season", "team", "player",
            "match", etc.
        provider: Provider name, e.g. "api_football" or "football_data".
        external_id: Provider-specific identifier string.
        internal_id: Primary key of the canonical entity row.
        entity_column: Column name on external_ids to store internal_id in
            ("team_id", "player_id", "match_id", "competition_id",
            "season_id").

    Returns:
        (ExternalId instance, created)
    """
    from db.models.external_id import ExternalId

    conflict_keys = {
        "entity_type": entity_type,
        "provider": provider,
        "external_id": external_id,
    }

    # Pre-check: if the mapping row already exists and already has the
    # entity_column set, do not overwrite it — preserves the internal/provider
    # ID boundary required by _resolve_match_fixture().
    stmt = select(ExternalId)
    for col_name, col_value in conflict_keys.items():
        stmt = stmt.where(getattr(ExternalId, col_name) == col_value)
    existing_check = await session.execute(stmt)
    existing_row = existing_check.scalar_one_or_none()

    values: dict[str, Any] = {}
    if existing_row is None or getattr(existing_row, entity_column) is None:
        values[entity_column] = internal_id

    result = await upsert_entity(
        session,
        ExternalId,
        conflict_keys,
        values,
        preserve_existing=True,
    )
    return result


# ─── Type-safe wrappers ─────────────────────────────────────────────────


async def upsert_competition(
    session: AsyncSession,
    slug: str,
    name: str,
    country: str | None = None,
    logo_url: str | None = None,
) -> tuple[Any, bool]:
    """Upsert a competition row. Conflict key: slug (unique)."""
    from db.models.competition import Competition

    values: dict[str, Any] = {"name": name}
    if country is not None:
        values["country"] = country
    if logo_url is not None:
        values["logo_url"] = logo_url

    return await upsert_entity(
        session,
        Competition,
        conflict_keys={"slug": slug},
        values=values,
        preserve_existing=True,
    )


async def upsert_season(
    session: AsyncSession,
    competition_id: int,
    label: str,
    start_date: Any | None = None,
    end_date: Any | None = None,
    availability_status: str | None = None,
) -> tuple[Any, bool]:
    """Upsert a season row. Conflict key: (competition_id, label)."""
    from db.models.season import Season

    values: dict[str, Any] = {}
    if start_date is not None:
        values["start_date"] = start_date
    if end_date is not None:
        values["end_date"] = end_date
    if availability_status is not None:
        values["availability_status"] = availability_status

    return await upsert_entity(
        session,
        Season,
        conflict_keys={"competition_id": competition_id, "label": label},
        values=values,
        preserve_existing=True,
    )


async def upsert_team(
    session: AsyncSession,
    slug: str,
    name: str,
    short_name: str | None = None,
    crest_url: str | None = None,
    founded: int | None = None,
    venue_id: int | None = None,
) -> tuple[Any, bool]:
    """Upsert a team row. Conflict key: slug (unique)."""
    from db.models.team import Team

    values: dict[str, Any] = {"name": name}
    if short_name is not None:
        values["short_name"] = short_name
    if crest_url is not None:
        values["crest_url"] = crest_url
    if founded is not None:
        values["founded"] = founded
    if venue_id is not None:
        values["venue_id"] = venue_id

    return await upsert_entity(
        session,
        Team,
        conflict_keys={"slug": slug},
        values=values,
        preserve_existing=True,
    )


async def upsert_player(
    session: AsyncSession,
    slug: str,
    name: str,
    position: str | None = None,
    number: int | None = None,
    nationality: str | None = None,
    date_of_birth: str | None = None,
    height_cm: int | None = None,
    foot: str | None = None,
) -> tuple[Any, bool]:
    """Upsert a player row. Conflict key: slug (unique)."""
    from db.models.player import Player

    values: dict[str, Any] = {"name": name}
    if position is not None:
        values["position"] = position
    if number is not None:
        values["number"] = number
    if nationality is not None:
        values["nationality"] = nationality
    if date_of_birth is not None:
        values["date_of_birth"] = date_of_birth
    if height_cm is not None:
        values["height_cm"] = height_cm
    if foot is not None:
        values["foot"] = foot

    return await upsert_entity(
        session,
        Player,
        conflict_keys={"slug": slug},
        values=values,
        preserve_existing=True,
    )


async def upsert_match(
    session: AsyncSession,
    slug: str,
    home_team_id: int,
    away_team_id: int,
    date: Any,
    competition_id: int | None = None,
    season_id: int | None = None,
    venue_id: int | None = None,
    referee_id: int | None = None,
    kickoff_time: Any | None = None,
    status: str | None = None,
    minute: int | None = None,
    home_score: int | None = None,
    away_score: int | None = None,
    attendance: int | None = None,
) -> tuple[Any, bool]:
    """Upsert a match row. Conflict key: slug (unique).

    Does NOT touch external_ids — match-to-provider-ID mapping is handled
    by upsert_external_id separately, preserving the internal/provider ID
    boundary required by _resolve_match_fixture().
    """
    from db.models.match import Match

    values: dict[str, Any] = {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "date": date,
    }
    if competition_id is not None:
        values["competition_id"] = competition_id
    if season_id is not None:
        values["season_id"] = season_id
    if venue_id is not None:
        values["venue_id"] = venue_id
    if referee_id is not None:
        values["referee_id"] = referee_id
    if kickoff_time is not None:
        values["kickoff_time"] = kickoff_time
    if status is not None:
        values["status"] = status
    if minute is not None:
        values["minute"] = minute
    if home_score is not None:
        values["home_score"] = home_score
    if away_score is not None:
        values["away_score"] = away_score
    if attendance is not None:
        values["attendance"] = attendance

    return await upsert_entity(
        session,
        Match,
        conflict_keys={"slug": slug},
        values=values,
        preserve_existing=True,
    )
