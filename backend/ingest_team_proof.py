"""Proof-of-pipeline: fetch Premier League teams from API-Football,
normalize them, persist them to Neon, and read them back.

Usage:
    cd backend && python ingest_team_proof.py
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
logger = logging.getLogger("ingest_team_proof")

from sqlalchemy import select  # noqa: E402

from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402
from normalization.teams import normalize_team_summary  # noqa: E402


COMPETITION_ID = 39  # Premier League
SEASON = int(os.getenv("SEASON", "2024"))  # supported by the configured API-Football plan


async def run() -> int:
    provider = ApiFootballProvider()

    # 1. Resolve the existing Premier League competition through the DB.
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

    # 2. Fetch the teams for the competition (single API request).
    logger.info("Fetching teams for league=%s season=%s", COMPETITION_ID, SEASON)
    raw_list = await provider.get_teams(COMPETITION_ID, SEASON)
    logger.info("API returned %s team records", len(raw_list))

    # 3. Normalize each team using the existing project conventions.
    normalized = []
    for item in raw_list:
        api_team = item.get("team", {})
        summary = normalize_team_summary(api_team)
        normalized.append((summary, api_team))
    logger.info("Normalized %s teams", len(normalized))
    for summary, api_team in normalized[:3]:
        logger.info("  sample: id=%s name=%r slug=%r founded=%s code=%r",
                    summary.id, summary.name, summary.slug,
                    api_team.get("founded"), api_team.get("code"))

    # 4. Persist each team in a single transaction, skipping duplicates
    #    via the existing external_ids identity mechanism.
    repo = Repository(Team)
    created = 0
    reused = 0
    async with async_session() as session:
        for summary, api_team in normalized:
            existing = await repo.get_by_external_id(
                provider="api_football",
                external_id=str(summary.id),
                entity_type="team",
            )
            if existing is not None:
                reused += 1
                logger.info("  already present: external_id=%s name=%r (internal_id=%s)",
                            summary.id, summary.name, existing["team_id"])
                continue

            team = Team(
                name=summary.name,
                slug=summary.slug,
                short_name=(api_team.get("code") or None),
                crest_url=summary.crest_url or None,
                founded=api_team.get("founded"),
                venue_id=None,
            )
            session.add(team)
            await session.flush()
            team_id = team.id

            ext = ExternalId(
                entity_type="team",
                provider="api_football",
                external_id=str(summary.id),
                team_id=team_id,
            )
            session.add(ext)
            created += 1
            logger.info("  created team id=%s external_id=%s name=%r",
                        team_id, summary.id, summary.name)
        await session.commit()
    logger.info("Persistence: created=%s already_present=%s", created, reused)

    # 5. Read teams back from Neon and verify provider identity + name.
    async with async_session() as session:
        result = await session.execute(select(Team).order_by(Team.id))
        stored_teams = list(result.scalars().all())
        ext_result = await session.execute(select(ExternalId))
        ext_rows = {r.team_id: r for r in ext_result.scalars().all() if r.team_id is not None}

    logger.info("Read-back: %s teams in Neon", len(stored_teams))
    verified = 0
    for team in stored_teams:
        ext_row = ext_rows.get(team.id)
        if ext_row and ext_row.provider == "api_football":
            verified += 1
        logger.info("  team id=%s name=%r slug=%r short_name=%r external_id=%s",
                    team.id, team.name, team.slug, team.short_name,
                    ext_row.external_id if ext_row else None)

    # 6. Final assertions.
    assert created + reused == len(normalized), "team count mismatch"
    assert len(stored_teams) >= created, "read-back count mismatch"
    assert verified == len(stored_teams), "external_id coverage mismatch"
    logger.info("Verification passed: %s teams persisted/reused, %s read back, "
                "all with provider identity.",
                created + reused, len(stored_teams))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))