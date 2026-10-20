"""Proof-of-pipeline: fetch EPL teams from API-Football,
persist them to Neon, and read them back.

Usage:
    cd backend && python ingest_team_proof_2023.py
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
logger = logging.getLogger("ingest_team_proof_2023")

from sqlalchemy import select  # noqa: E402

from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402


COMPETITION_ID = 39  # Premier League (API-Football)
SEASON_YEAR = 2023


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
    logger.info("Resolved competition: internal_id=%s name=%r", competition.id, competition.name)

    # 2. Fetch teams from API-Football.
    logger.info("Fetching teams for league=%s season=%s", COMPETITION_ID, SEASON_YEAR)
    teams_raw = await provider.get_teams(COMPETITION_ID, SEASON_YEAR)
    logger.info("API returned %s teams", len(teams_raw))

    # 3. Persist or reuse each team.
    created = 0
    reused = 0
    for t in teams_raw:
        api_team = t.get("team", t)
        api_team_id = api_team.get("id")
        if api_team_id is None:
            logger.warning("Skipping team with no id")
            continue

        repo = Repository(Team)
        existing = await repo.get_by_external_id(
            provider="api_football",
            external_id=str(api_team_id),
            entity_type="team",
        )
        if existing is not None:
            internal_id = existing["team_id"]
            reused += 1
            logger.info("  already present: %s (internal_id=%s)", api_team.get("name"), internal_id)
            continue

        name = api_team.get("name", "")
        slug = name.lower().replace(" ", "-").replace(".", "")
        async with async_session() as session:
            team = Team(
                name=name,
                slug=slug,
                short_name=api_team.get("code"),
                crest_url=api_team.get("logo"),
                founded=api_team.get("founded"),
            )
            session.add(team)
            await session.flush()
            internal_id = team.id

            ext = ExternalId(
                entity_type="team",
                provider="api_football",
                external_id=str(api_team_id),
                team_id=internal_id,
            )
            session.add(ext)
            await session.commit()
            created += 1
            logger.info("  created: %s (internal_id=%s)", name, internal_id)

    logger.info("Persistence: created=%s already_present=%s", created, reused)

    # 4. Read back and verify.
    async with async_session() as session:
        result = await session.execute(select(Team))
        stored = list(result.scalars().all())
    logger.info("Read-back: %s teams in Neon", len(stored))

    # 5. Final assertions.
    assert created + reused == len(teams_raw), "team count mismatch"
    logger.info("Verification passed: %s teams persisted/reused, %s total in DB.", created + reused, len(stored))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
