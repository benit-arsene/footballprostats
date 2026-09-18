"""Persistence boundary — repository pattern for database operations.

This layer isolates the rest of the application from the database.
All DB access goes through repository methods. The provider layer
never touches the DB directly — it returns canonical models, and
the persistence layer decides whether/how to store them.
"""

from __future__ import annotations

from typing import Any

from db.session import async_session
from db.base import Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class Repository:
    """Generic repository for a SQLAlchemy model."""

    def __init__(self, model: type[Base], session: AsyncSession | None = None) -> None:
        self.model = model
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return async_session()

    async def get_by_id(self, entity_id: int) -> Base | None:
        """Fetch a single record by primary key."""
        session = await self._get_session()
        result = await session.execute(select(self.model).where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Base]:
        """Fetch all records."""
        session = await self._get_session()
        result = await session.execute(select(self.model))
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Base | None:
        """Fetch a single record by slug (if the model has a slug column)."""
        session = await self._get_session()
        result = await session.execute(select(self.model).where(self.model.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self, provider: str, external_id: str, entity_type: str
    ) -> dict | None:
        """Look up an entity via external_ids table.

        Returns dict with entity info if found, None otherwise.
        """
        from db.models.external_id import ExternalId
        session = await self._get_session()
        result = await session.execute(
            select(ExternalId)
            .where(ExternalId.provider == provider)
            .where(ExternalId.external_id == external_id)
            .where(ExternalId.entity_type == entity_type)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "entity_type": row.entity_type,
            "provider": row.provider,
            "external_id": row.external_id,
            "team_id": row.team_id,
            "player_id": row.player_id,
            "match_id": row.match_id,
            "competition_id": row.competition_id,
            "season_id": row.season_id,
        }

    async def create_external_id(
        self,
        entity_type: str,
        provider: str,
        external_id: str,
        internal_id: int,
    ) -> None:
        """Create an external ID mapping.

        Assumes the canonical entity with internal_id already exists.
        """
        from db.models.external_id import ExternalId
        session = await self._get_session()
        ext = ExternalId(
            entity_type=entity_type,
            provider=provider,
            external_id=external_id,
            team_id=internal_id if entity_type == "team" else None,
            player_id=internal_id if entity_type == "player" else None,
            match_id=internal_id if entity_type == "match" else None,
            competition_id=internal_id if entity_type == "competition" else None,
            season_id=internal_id if entity_type == "season" else None,
        )
        session.add(ext)
        await session.flush()
