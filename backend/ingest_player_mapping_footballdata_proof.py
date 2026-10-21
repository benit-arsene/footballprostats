"""Safe football-data.org player ID mapping proof.

Usage:
    cd backend && python ingest_player_mapping_footballdata_proof.py
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
logger = logging.getLogger("player_mapping_footballdata")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.player import Player  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.football_data.client import FootballDataProvider  # noqa: E402


COMPETITION_ID = 39
SEASON_YEAR = get_season_year()


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


ALIASES = {
    "erlinghaaland": "ehaaland",
    "joopedro": "jopedro",
    "alexanderisak": "aisak",
    "marcustavernier": "mtavernier",
    "morganrogers": "mrogers",
    "bryanmbeumo": "bmbeumo",
    "bukayosaka": "bsaka",
}


async def run() -> int:
    provider = FootballDataProvider()
    scorers = await provider.get_top_scorers(COMPETITION_ID, SEASON_YEAR)
    logger.info("Fetched %s scorers from football-data.org", len(scorers))

    async with async_session() as session:
        result = await session.execute(select(Player))
        db_players = list(result.scalars().all())

    norm_map: dict[str, list[Player]] = {}
    for p in db_players:
        norm_map.setdefault(_normalize(p.name), []).append(p)

    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.provider == "football_data",
                ExternalId.entity_type == "player",
            )
        )
        existing_mappings = {e.external_id: e for e in result.scalars().all()}

    written = 0
    skipped = 0
    conflicts = 0
    for entry in scorers:
        player_info = entry.get("player", {}) or {}
        fd_id = str(player_info.get("id"))
        fd_name = player_info.get("name", "")

        if fd_id in existing_mappings:
            logger.info("already mapped: fd_id=%s (%s)", fd_id, fd_name)
            skipped += 1
            continue

        norm = _normalize(fd_name)
        lookup = ALIASES.get(norm, norm)
        candidates = norm_map.get(lookup, [])
        if len(candidates) != 1:
            logger.info("skip (candidates=%d): fd_id=%s name=%r", len(candidates), fd_id, fd_name)
            skipped += 1
            continue

        target = candidates[0]
        # conflict check
        conflict = any(em.team_id is None and em.player_id == target.id for em in existing_mappings.values()) if False else False
        # check existing mapping for this player
        async with async_session() as session:
            result = await session.execute(
                select(ExternalId).where(
                    ExternalId.provider == "football_data",
                    ExternalId.entity_type == "player",
                    ExternalId.player_id == target.id,
                )
            )
            existing_for_player = result.scalar_one_or_none()
        if existing_for_player is not None:
            logger.warning("conflict: player %s already mapped to %s", target.name, existing_for_player.external_id)
            conflicts += 1
            continue

        async with async_session() as session:
            ext = ExternalId(
                entity_type="player",
                provider="football_data",
                external_id=fd_id,
                player_id=target.id,
            )
            session.add(ext)
            await session.commit()
        written += 1
        logger.info("MAPPED: fd_id=%s (%s) -> internal_id=%s (%s)", fd_id, fd_name, target.id, target.name)

    logger.info("Summary: written=%s skipped=%s conflicts=%s", written, skipped, conflicts)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
