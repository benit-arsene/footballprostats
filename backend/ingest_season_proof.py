"""Proof-of-pipeline: fetch a Premier League season from API-Football,
normalize it, persist it to Neon, link it to the existing Competition,
and read it back.

Usage:
    cd backend && python ingest_season_proof.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_season_proof")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from datetime import datetime  # noqa: E402

from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.season import Season  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402


COMPETITION_ID = 39  # Premier League
SEASON_YEAR = 2024  # accessible on the configured API-Football plan


def _season_label(year: int) -> str:
    """Project convention for a season label (see config.get_season_year)."""
    return f"{year}/{year + 1}"


def _parse_date(value: str | None) -> datetime | None:
    """Parse an ISO-8601 date string into a datetime (or None)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def run() -> int:
    provider = ApiFootballProvider()

    # 1. Resolve the existing Premier League Competition from Neon.
    async with async_session() as session:
        comp_result = await session.execute(select(Competition))
        competition = next(
            (c for c in comp_result.scalars().all() if c.name == "Premier League"),
            None,
        )
    if competition is None:
        logger.error("No Premier League Competition row found in Neon")
        return 1
    logger.info("Resolved competition: internal_id=%s name=%r",
                competition.id, competition.name)

    # 2. Fetch the season coverage list for the competition (single request).
    logger.info("Fetching seasons for league=%s", COMPETITION_ID)
    seasons = await provider.get_seasons(COMPETITION_ID)
    logger.info("API returned %s season records", len(seasons))

    api_season = next((s for s in seasons if s.get("year") == SEASON_YEAR), None)
    if api_season is None:
        logger.error("Season %s not present in provider response", SEASON_YEAR)
        return 1
    logger.info("Provider season %s: start=%s end=%s current=%s",
                api_season.get("year"), api_season.get("start"),
                api_season.get("end"), api_season.get("current"))

    # 3. Normalize into the internal Season representation.
    label = _season_label(SEASON_YEAR)
    start_date = _parse_date(api_season.get("start"))
    end_date = _parse_date(api_season.get("end"))
    logger.info("Normalized season: label=%r start=%s end=%s", label, start_date, end_date)

    # 4. Persist or reuse the Season, avoiding duplicates via the existing
    #    external_ids identity mechanism (provider=api_football,
    #    external_id=<league id>/<season year>, entity_type=season).
    external_id = f"{COMPETITION_ID}/{SEASON_YEAR}"
    repo = Repository(Season)
    existing = await repo.get_by_external_id(
        provider="api_football",
        external_id=external_id,
        entity_type="season",
    )

    if existing is not None:
        season_id = existing["season_id"]
        logger.info("Season already present (external_id=%s, internal_id=%s)",
                    external_id, season_id)
    else:
        async with async_session() as session:
            season = Season(
                competition_id=competition.id,
                label=label,
                start_date=start_date,
                end_date=end_date,
                availability_status="imported",
                import_job_id=None,
                last_import_attempt=None,
            )
            session.add(season)
            await session.flush()
            season_id = season.id

            ext = ExternalId(
                entity_type="season",
                provider="api_football",
                external_id=external_id,
                competition_id=competition.id,
                season_id=season_id,
            )
            session.add(ext)
            await session.commit()
        logger.info("Created season id=%s competition_id=%s label=%r",
                    season_id, competition.id, label)

    # 5. Read the Season back from Neon and verify the FK relationship.
    async with async_session() as session:
        result = await session.execute(
            select(Season).where(Season.id == season_id)
        )
        stored = result.scalar_one_or_none()
        ext_result = await session.execute(
            select(ExternalId).where(ExternalId.season_id == season_id)
        )
        ext_row = ext_result.scalar_one_or_none()

    if stored is None:
        logger.error("Read-back failed: no Season with id=%s", season_id)
        return 1

    logger.info("Read-back OK:")
    logger.info("  season.id              = %s", stored.id)
    logger.info("  season.competition_id  = %s", stored.competition_id)
    logger.info("  season.label           = %r", stored.label)
    logger.info("  season.start_date      = %s", stored.start_date)
    logger.info("  season.end_date        = %s", stored.end_date)
    logger.info("  season.availability    = %r", stored.availability_status)
    if ext_row is not None:
        logger.info("  external_id.provider   = %r", ext_row.provider)
        logger.info("  external_id.external_id= %r", ext_row.external_id)
        logger.info("  external_id.entity_type= %r", ext_row.entity_type)

    # 6. Verify the ORM relationship from both directions.
    assert stored.competition_id == competition.id, "FK mismatch"
    logger.info("Season.competition_id == Competition.id (%s) OK",
                competition.id)

    # Reload the competition and traverse the relationship (eager load so
    # the collection is resolved while the session is still open).
    async with async_session() as session:
        result = await session.execute(
            select(Competition)
            .options(selectinload(Competition.seasons))
            .where(Competition.id == competition.id)
        )
        comp = result.scalar_one()
        related_seasons = list(comp.seasons)
    matched = [s for s in related_seasons if s.id == season_id]
    assert matched, "Competition.seasons did not include the persisted Season"
    logger.info("Competition.seasons relationship verified: %s season(s) linked",
                len(related_seasons))

    # 7. Final assertions.
    assert stored.label == label
    assert ext_row is not None
    assert ext_row.provider == "api_football"
    assert ext_row.external_id == external_id
    assert ext_row.entity_type == "season"
    assert ext_row.season_id == season_id
    logger.info("Verification passed: season persisted, FK correct, "
                "relationship bidirectional, external identity intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))