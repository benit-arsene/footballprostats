"""Proof-of-pipeline: fetch one competition from API-Football, normalize it,
persist it to Neon PostgreSQL, and read it back.

Usage:
    cd backend && python ingest_competition_proof.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os

# Ensure the backend package is importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_proof")

from sqlalchemy import select  # noqa: E402

from db.base import Base  # noqa: E402
from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402
from normalization.competitions import normalize_league_summary  # noqa: E402


# One known API-Football competition supported by the project config.
COMPETITION_ID = 39  # Premier League


async def run() -> int:
    provider = ApiFootballProvider()

    # 1. Fetch one competition from API-Football (single request).
    logger.info("Fetching competition id=%s from API-Football", COMPETITION_ID)
    raw = await provider.get_competition(COMPETITION_ID)
    if not raw:
        logger.error("API returned no data for competition %s", COMPETITION_ID)
        return 1

    league_dict = raw.get("league", {})
    country_dict = raw.get("country")

    # 2. Normalize using the existing project conventions.
    normalized = normalize_league_summary(league_dict, country_dict)
    logger.info("Normalized: id=%s name=%r slug=%r country=%r",
                normalized.id, normalized.name, normalized.slug, normalized.country)

    # 3. Determine existing identity via the external_ids table (provider
    #    "api_football", external_id = API-Football league id, entity_type
    #    "competition"). Reuse the project's existing identity mechanism.
    repo = Repository(Competition)
    existing = await repo.get_by_external_id(
        provider="api_football",
        external_id=str(COMPETITION_ID),
        entity_type="competition",
    )

    if existing is not None:
        logger.info("Competition already present (external_id=%s, internal_id=%s)",
                    COMPETITION_ID, existing["competition_id"])
        internal_id = existing["competition_id"]
    else:
        # Persist a new Competition row (internal PK auto-generated; the
        # provider identity is stored in external_ids).
        async with async_session() as session:
            competition = Competition(
                name=normalized.name,
                slug=normalized.slug,
                country=normalized.country or None,
                logo_url=normalized.logo_url or None,
            )
            session.add(competition)
            await session.flush()
            internal_id = competition.id

            ext = ExternalId(
                entity_type="competition",
                provider="api_football",
                external_id=str(COMPETITION_ID),
                competition_id=internal_id,
            )
            session.add(ext)
            await session.commit()
        logger.info("Persisted new competition (internal_id=%s)", internal_id)

    # 4. Read the competition back from Neon and verify.
    async with async_session() as session:
        result = await session.execute(
            select(Competition).where(Competition.id == internal_id)
        )
        stored = result.scalar_one_or_none()

    if stored is None:
        logger.error("Read-back failed: no row with id=%s", internal_id)
        return 1

    # Also read the external_id mapping back.
    async with async_session() as session:
        ext_result = await session.execute(
            select(ExternalId).where(ExternalId.competition_id == internal_id)
        )
        ext_row = ext_result.scalar_one_or_none()

    logger.info("Read-back OK:")
    logger.info("  competition.id        = %s", stored.id)
    logger.info("  competition.name      = %r", stored.name)
    logger.info("  competition.slug      = %r", stored.slug)
    logger.info("  competition.country   = %r", stored.country)
    logger.info("  competition.logo_url  = %r", stored.logo_url)
    if ext_row is not None:
        logger.info("  external_id.provider  = %r", ext_row.provider)
        logger.info("  external_id.external_id = %r", ext_row.external_id)
        logger.info("  external_id.entity_type = %r", ext_row.entity_type)

    # Final assertion: provider identity + name survived the round trip.
    assert ext_row is not None, "external_id mapping missing"
    assert ext_row.provider == "api_football"
    assert ext_row.external_id == str(COMPETITION_ID)
    assert ext_row.entity_type == "competition"
    assert stored.name == normalized.name
    assert stored.slug == normalized.slug
    logger.info("Verification passed: provider identity and name match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))