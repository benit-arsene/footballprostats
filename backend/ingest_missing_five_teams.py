"""Create internal Team records for the five football-data.org clubs that
have no existing internal team, and map their football-data.org IDs.

Usage:
    cd backend && python ingest_missing_five_teams.py
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
logger = logging.getLogger("ingest_missing_five_teams")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.football_data.client import FootballDataProvider  # noqa: E402
from providers.football_data.adapters import FootballDataAdapters  # noqa: E402


COMPETITION_ID = 39
SEASON_YEAR = get_season_year()

# football-data.org team names we need to create (verified from provider output).
TARGET_NAMES = {"Leeds United FC", "Hull City AFC", "Ipswich Town FC", "Coventry City FC", "Sunderland AFC"}


def _make_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("&", "and")


async def run() -> int:
    provider = FootballDataProvider()
    rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)

    fd_teams = []
    for r in rows_raw:
        ts = FootballDataAdapters.team_summary(r.get("team", {}))
        if ts.name in TARGET_NAMES:
            fd_teams.append((str(ts.id), ts.name))

    logger.info("Found %s target teams in provider response", len(fd_teams))

    created_teams = 0
    reused_teams = 0
    created_mappings = 0
    reused_mappings = 0

    for fd_id, fd_name in fd_teams:
        repo = Repository(Team)
        existing_fd = await repo.get_by_external_id(
            provider="football_data",
            external_id=fd_id,
            entity_type="team",
        )
        if existing_fd is not None:
            logger.info("  already mapped: %s (fd_id=%s) -> internal_id=%s", fd_name, fd_id, existing_fd["team_id"])
            reused_mappings += 1
            continue

        # Check if an internal team with the same normalized name exists.
        async with async_session() as session:
            result = await session.execute(select(Team))
            db_teams = list(result.scalars().all())

        # Find by slug or name (exact-ish).
        match = None
        for t in db_teams:
            if t.name.lower() == fd_name.lower() or t.slug == _make_slug(fd_name):
                match = t
                break

        if match is None:
            # Create new team.
            async with async_session() as session:
                team = Team(
                    name=fd_name,
                    slug=_make_slug(fd_name),
                    short_name=None,
                    crest_url=None,
                )
                session.add(team)
                await session.flush()
                internal_id = team.id
                ext = ExternalId(
                    entity_type="team",
                    provider="football_data",
                    external_id=fd_id,
                    team_id=internal_id,
                )
                session.add(ext)
                await session.commit()
            created_teams += 1
            created_mappings += 1
            logger.info("  created team + mapping: %s (fd_id=%s) -> internal_id=%s", fd_name, fd_id, internal_id)
        else:
            # Reuse existing team, add mapping.
            async with async_session() as session:
                # Check no existing football_data mapping for this team.
                result = await session.execute(
                    select(ExternalId).where(
                        ExternalId.provider == "football_data",
                        ExternalId.entity_type == "team",
                        ExternalId.team_id == match.id,
                    )
                )
                existing_for_team = result.scalar_one_or_none()
                if existing_for_team is not None:
                    logger.info("  team %s already has mapping %s — skipping", match.name, existing_for_team.external_id)
                    reused_mappings += 1
                    continue
                ext = ExternalId(
                    entity_type="team",
                    provider="football_data",
                    external_id=fd_id,
                    team_id=match.id,
                )
                session.add(ext)
                await session.commit()
            reused_teams += 1
            created_mappings += 1
            logger.info("  reused team %s, created mapping fd_id=%s", match.name, fd_id)

    logger.info("Summary: created_teams=%s reused_teams=%s created_mappings=%s reused_mappings=%s",
                created_teams, reused_teams, created_mappings, reused_mappings)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
