"""Safe football-data.org team ID mapping proof.

Fetches current-season standings from football-data.org, matches teams
to existing internal teams by normalized name, and persists only
unambiguous mappings into external_ids.

Usage:
    cd backend && python ingest_team_mapping_footballdata_proof.py
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("team_mapping_footballdata")

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


ALIASES: dict[str, str] = {
    "newcastleunited": "newcastle",
    "tottenhamhotspur": "tottenham",
    "brightonhovealbion": "brighton",
}


def _normalize(name: str) -> str:
    n = name.lower().strip()
    # Remove common suffixes/prefixes
    n = re.sub(r"\b(fc|afc|cf|sc)\b", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n


async def run() -> int:
    provider = FootballDataProvider()

    # 1. Fetch standings to get football-data teams.
    rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
    logger.info("Fetched %s standings rows from football-data.org", len(rows_raw))

    fd_teams = []
    for r in rows_raw:
        ts = FootballDataAdapters.team_summary(r.get("team", {}))
        fd_teams.append((str(ts.id), ts.name))

    # 2. Load existing teams + their api_football external ids.
    async with async_session() as session:
        result = await session.execute(select(Team))
        db_teams = list(result.scalars().all())

    # Build normalized name -> list of db teams
    norm_map: dict[str, list[Team]] = {}
    for t in db_teams:
        norm_map.setdefault(_normalize(t.name), []).append(t)

    # 3. Load existing football_data mappings.
    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.provider == "football_data",
                ExternalId.entity_type == "team",
            )
        )
        existing_fd_mappings = {e.external_id: e for e in result.scalars().all()}

    # 4. Process each candidate.
    written = 0
    skipped = 0
    conflicts = 0
    for fd_id, fd_name in fd_teams:
        norm = _normalize(fd_name)
        lookup = ALIASES.get(norm, norm)
        candidates = norm_map.get(lookup, [])
        # Report
        logger.info("Candidate: fd_id=%s name=%r normalized=%r db_matches=%s",
                    fd_id, fd_name, norm, [t.name for t in candidates])

        # Already mapped?
        if fd_id in existing_fd_mappings:
            em = existing_fd_mappings[fd_id]
            logger.info("  already mapped to internal_id=%s — skipping", em.team_id)
            skipped += 1
            continue

        # Unambiguous match?
        if len(candidates) != 1:
            logger.info("  ambiguous or no match (%d candidates) — skipping for manual review", len(candidates))
            skipped += 1
            continue

        target = candidates[0]
        # Check if this internal team is already mapped to a different fd id.
        conflict = False
        for eid, em in existing_fd_mappings.items():
            if em.team_id == target.id and eid != fd_id:
                conflict = True
                break
        if conflict:
            logger.warning("  CONFLICT: internal team %s already mapped to another fd id — skipping", target.name)
            conflicts += 1
            continue

        # Also check external_ids table for any existing mapping of this team to football_data.
        async with async_session() as session:
            result = await session.execute(
                select(ExternalId).where(
                    ExternalId.provider == "football_data",
                    ExternalId.entity_type == "team",
                    ExternalId.team_id == target.id,
                )
            )
            existing_for_team = result.scalar_one_or_none()
        if existing_for_team is not None:
            logger.warning("  team %s already has a football_data mapping (%s) — skipping",
                           target.name, existing_for_team.external_id)
            conflicts += 1
            continue

        # Persist.
        async with async_session() as session:
            ext = ExternalId(
                entity_type="team",
                provider="football_data",
                external_id=fd_id,
                team_id=target.id,
            )
            session.add(ext)
            await session.commit()
        written += 1
        logger.info("  MAPPED: fd_id=%s (%s) -> internal_id=%s (%s)", fd_id, fd_name, target.id, target.name)

    logger.info("Summary: written=%s skipped=%s conflicts=%s", written, skipped, conflicts)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
