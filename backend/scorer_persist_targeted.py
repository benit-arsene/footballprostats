"""Targeted top-scorer persistence verification (no standings/fixtures)."""

from __future__ import annotations

import asyncio
import logging
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("scorer_persist")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.player import Player  # noqa: E402
from db.models.player_season_stat import PlayerSeasonStat  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.models.season import Season  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
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
    logger.info("Fetched %s scorers", len(scorers))

    async with async_session() as session:
        seasons = list((await session.execute(select(Season))).scalars().all())
        season = next(s for s in seasons if s.label == f"{SEASON_YEAR}/{SEASON_YEAR + 1}")
        season_id = season.id

    created = 0
    reused = 0
    skipped = 0
    for entry in scorers:
        player_info = entry.get("player", {}) or {}
        fd_id = str(player_info.get("id"))
        goals = entry.get("goals") or 0
        assists = entry.get("assists") or 0

        repo = Repository(Player)
        existing = await repo.get_by_external_id(provider="football_data", external_id=fd_id, entity_type="player")
        if existing is None:
            async with async_session() as session:
                players = list((await session.execute(select(Player))).scalars().all())
            norm_fd = _normalize(player_info.get("name", ""))
            lookup = ALIASES.get(norm_fd, norm_fd)
            cands = [p for p in players if _normalize(p.name) == lookup]
            if len(cands) == 1:
                target = cands[0]
                async with async_session() as session:
                    ext = ExternalId(entity_type="player", provider="football_data", external_id=fd_id, player_id=target.id)
                    session.add(ext)
                    await session.commit()
                existing = await repo.get_by_external_id(provider="football_data", external_id=fd_id, entity_type="player")
            else:
                logger.warning("skip (candidates=%d): %s", len(cands), player_info.get("name"))
                skipped += 1
                continue
        if existing is None:
            skipped += 1
            continue
        internal_id = existing["player_id"]

        # resolve team
        team_info = entry.get("team", {}) or {}
        fd_team_id = str(team_info.get("id"))
        team_ext = await Repository(Team).get_by_external_id(provider="football_data", external_id=fd_team_id, entity_type="team")
        if team_ext is None:
            logger.warning("no team mapping for %s", fd_team_id)
            skipped += 1
            continue
        team_id = team_ext["team_id"]

        async with async_session() as session:
            result = await session.execute(
                select(PlayerSeasonStat).where(
                    PlayerSeasonStat.player_id == internal_id,
                    PlayerSeasonStat.season_id == season_id,
                    PlayerSeasonStat.team_id == team_id,
                )
            )
            existing_stat = result.scalar_one_or_none()
            if existing_stat is not None:
                if goals and not existing_stat.goals:
                    existing_stat.goals = goals
                if assists and not existing_stat.assists:
                    existing_stat.assists = assists
                await session.commit()
                reused += 1
                continue
            pss = PlayerSeasonStat(
                player_id=internal_id,
                season_id=season_id,
                team_id=team_id,
                goals=goals,
                assists=assists,
                appearances=0,
            )
            session.add(pss)
            await session.commit()
            created += 1

    logger.info("Top scorers persistence: created=%s reused=%s skipped=%s", created, reused, skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
