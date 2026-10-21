"""Proof-of-pipeline: ingest Premier League players from API-Football.

Usage:
    cd backend && python ingest_players_proof.py
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
logger = logging.getLogger("ingest_players_proof")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.player import Player  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402


SEASON_YEAR = 2024


def _make_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")


async def run() -> int:
    provider = ApiFootballProvider()

    # 1. Resolve teams with api_football external ids.
    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.provider == "api_football",
                ExternalId.entity_type == "team",
            )
        )
        ext_rows = list(result.scalars().all())

    team_ext_map = {e.team_id: e.external_id for e in ext_rows if e.team_id}
    logger.info("Teams with api_football mapping: %s", len(team_ext_map))

    # 2. Pre-load existing player external ids (one query).
    async with async_session() as session:
        result = await session.execute(
            select(ExternalId).where(
                ExternalId.provider == "api_football",
                ExternalId.entity_type == "player",
            )
        )
        existing_ext = {e.external_id: e.player_id for e in result.scalars().all()}

    created = 0
    reused = 0
    for internal_team_id, api_team_id in team_ext_map.items():
        try:
            players_raw = await provider.get_team_players(int(api_team_id), SEASON_YEAR)
        except Exception as e:
            logger.warning("Failed to fetch players for team %s: %s", api_team_id, e)
            continue
        logger.info("Team %s: %s players", api_team_id, len(players_raw))

        new_players = []
        new_exts = []
        for p in players_raw:
            player_info = p.get("player", {}) if isinstance(p, dict) else {}
            api_player_id = player_info.get("id")
            if api_player_id is None:
                continue
            aid = str(api_player_id)
            if aid in existing_ext:
                reused += 1
                continue
            name = player_info.get("name", "")
            new_players.append((name, aid))

        if not new_players:
            continue

        # Batch insert in one session/transaction.
        async with async_session() as session:
            for name, aid in new_players:
                player = Player(name=name, slug=_make_slug(name))
                session.add(player)
                await session.flush()
                pid = player.id
                ext = ExternalId(
                    entity_type="player",
                    provider="api_football",
                    external_id=aid,
                    player_id=pid,
                )
                session.add(ext)
                existing_ext[aid] = pid
                created += 1
            await session.commit()

    logger.info("Player ingestion: created=%s reused=%s", created, reused)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
