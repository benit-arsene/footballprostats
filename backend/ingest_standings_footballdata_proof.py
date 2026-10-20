"""Proof-of-pipeline: fetch current-season standings from football-data.org,
persist them to Neon, and read them back.

Usage:
    cd backend && python ingest_standings_footballdata_proof.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest_standings_footballdata_proof")

from sqlalchemy import select  # noqa: E402

from config import get_season_year  # noqa: E402
from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.season import Season  # noqa: E402
from db.models.standing_row import StandingRow  # noqa: E402
from db.models.standing_snapshot import StandingSnapshot  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.football_data.client import FootballDataProvider  # noqa: E402
from providers.football_data.adapters import FootballDataAdapters  # noqa: E402


COMPETITION_ID = 39  # Premier League (API-Football internal)
FD_CODE = "PL"  # football-data.org code
SEASON_YEAR = get_season_year()
SEASON_LABEL = f"{SEASON_YEAR}/{SEASON_YEAR + 1}"
SNAPSHOT_LABEL = f"EPL {SEASON_LABEL} football-data.org standings"
SEASON_EXTERNAL_ID = f"{FD_CODE}/{SEASON_YEAR}"


async def run() -> int:
    provider = FootballDataProvider()

    # 1. Resolve competition.
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

    # 2. Resolve or create the current season.
    repo_season = Repository(Season)
    existing_season = await repo_season.get_by_external_id(
        provider="football_data",
        external_id=SEASON_EXTERNAL_ID,
        entity_type="season",
    )
    if existing_season is not None:
        season_id = existing_season["season_id"]
        logger.info("Season already present (external_id=%s, internal_id=%s)", SEASON_EXTERNAL_ID, season_id)
    else:
        async with async_session() as session:
            season = Season(
                competition_id=competition.id,
                label=SEASON_LABEL,
                availability_status="imported",
            )
            session.add(season)
            await session.flush()
            season_id = season.id
            ext = ExternalId(
                entity_type="season",
                provider="football_data",
                external_id=SEASON_EXTERNAL_ID,
                competition_id=competition.id,
                season_id=season_id,
            )
            session.add(ext)
            await session.commit()
        logger.info("Created season id=%s label=%r", season_id, SEASON_LABEL)

    # 3. Fetch standings.
    logger.info("Fetching standings via football-data.org for league=%s season=%s", COMPETITION_ID, SEASON_YEAR)
    rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
    logger.info("Provider returned %s standings rows", len(rows_raw))

    # 4. Create or reuse snapshot.
    async with async_session() as session:
        snap_result = await session.execute(
            select(StandingSnapshot).where(
                StandingSnapshot.season_id == season_id,
                StandingSnapshot.label == SNAPSHOT_LABEL,
            )
        )
        snapshot = snap_result.scalar_one_or_none()
        if snapshot is None:
            snapshot = StandingSnapshot(
                season_id=season_id,
                matchday=None,
                label=SNAPSHOT_LABEL,
                snapshot_date=datetime.now(),
            )
            session.add(snapshot)
            await session.flush()
            created_snapshot = True
        else:
            created_snapshot = False
        snapshot_id = snapshot.id
        await session.commit()
    logger.info("StandingSnapshot %s (id=%s)", "created" if created_snapshot else "already present", snapshot_id)

    # 5. Persist rows, mapping teams via football_data external_ids.
    created_rows = 0
    reused_rows = 0
    skipped = 0
    for api_row in rows_raw:
        team_summary = FootballDataAdapters.team_summary(api_row.get("team", {}))
        fd_team_id = str(team_summary.id)
        repo = Repository(Team)
        existing_team = await repo.get_by_external_id(
            provider="football_data",
            external_id=fd_team_id,
            entity_type="team",
        )
        if existing_team is None:
            logger.warning("No football_data external_id mapping for team %s (%s) — skipping", fd_team_id, team_summary.name)
            skipped += 1
            continue
        internal_team_id = existing_team["team_id"]

        async with async_session() as session:
            row_result = await session.execute(
                select(StandingRow).where(
                    StandingRow.standing_snapshot_id == snapshot_id,
                    StandingRow.team_id == internal_team_id,
                )
            )
            existing_row = row_result.scalar_one_or_none()
            if existing_row is not None:
                reused_rows += 1
                continue
            sr = FootballDataAdapters.standing_row(api_row)
            row = StandingRow(
                standing_snapshot_id=snapshot_id,
                team_id=internal_team_id,
                position=sr.position,
                played=sr.played,
                won=sr.won,
                drawn=sr.drawn,
                lost=sr.lost,
                goals_for=sr.gf,
                goals_against=sr.ga,
                goal_difference=sr.gd,
                points=sr.points,
                form="".join(sr.form) if isinstance(sr.form, list) else str(sr.form or ""),
            )
            session.add(row)
            await session.commit()
            created_rows += 1

    logger.info("Persistence: created=%s already_present=%s skipped=%s", created_rows, reused_rows, skipped)

    # 6. Read back.
    async with async_session() as session:
        result = await session.execute(
            select(StandingRow).where(StandingRow.standing_snapshot_id == snapshot_id)
        )
        stored = list(result.scalars().all())
    logger.info("Read-back: %s standing rows in Neon", len(stored))

    if skipped > 0:
        logger.warning("BLOCKER: %s teams skipped because no football_data external_id mappings exist in the database.", skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
