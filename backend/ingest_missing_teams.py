"""Ingest the 3 missing teams (Luton, Burnley, Sheffield Utd) for 2023/2024."""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_missing_teams")

from sqlalchemy import select  # noqa: E402

from db.models.external_id import ExternalId  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402
from normalization.teams import normalize_team_summary  # noqa: E402


async def run() -> int:
    provider = ApiFootballProvider()
    repo = Repository(Team)

    for tid in [1359, 44, 62]:
        existing = await repo.get_by_external_id(
            provider="api_football",
            external_id=str(tid),
            entity_type="team",
        )
        if existing is not None:
            logger.info("Team %s already present (internal_id=%s)", tid, existing["team_id"])
            continue

        raw = await provider.get_team(tid)
        if not raw:
            logger.error("No data for team %s", tid)
            continue

        api_team = raw.get("team", raw)
        summary = normalize_team_summary(api_team)

        async with async_session() as session:
            team = Team(
                name=summary.name,
                slug=summary.slug,
                short_name=api_team.get("code"),
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
                external_id=str(tid),
                team_id=team_id,
            )
            session.add(ext)
            await session.commit()
        logger.info("Created team id=%s external_id=%s name=%r", team_id, tid, summary.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))