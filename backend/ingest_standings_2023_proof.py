"""Proof-of-pipeline: fetch EPL 2023/2024 standings from API-Football,
persist the season, snapshot, and rows to Neon, and read them back.

Usage:
    cd backend && python ingest_standings_2023_proof.py
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
logger = logging.getLogger("ingest_standings_2023_proof")

from sqlalchemy import select  # noqa: E402

from db.models.competition import Competition  # noqa: E402
from db.models.external_id import ExternalId  # noqa: E402
from db.models.season import Season  # noqa: E402
from db.models.standing_row import StandingRow  # noqa: E402
from db.models.standing_snapshot import StandingSnapshot  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from persistence.repository import Repository  # noqa: E402
from providers.api_football.client import ApiFootballProvider  # noqa: E402
from providers.api_football.adapters import ApiFootballAdapters  # noqa: E402


COMPETITION_ID = 39  # Premier League (API-Football)
SEASON_YEAR = 2023
SEASON_LABEL = f"{SEASON_YEAR}/{SEASON_YEAR + 1}"
SNAPSHOT_LABEL = f"EPL {SEASON_YEAR}/{SEASON_YEAR + 1} Final Standings"
SEASON_EXTERNAL_ID = f"{COMPETITION_ID}/{SEASON_YEAR}"


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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

    # 2. Resolve or create the 2023/2024 Season.
    repo_season = Repository(Season)
    existing_season = await repo_season.get_by_external_id(
        provider="api_football",
        external_id=SEASON_EXTERNAL_ID,
        entity_type="season",
    )
    if existing_season is not None:
        season_id = existing_season["season_id"]
        logger.info("Season already present (external_id=%s, internal_id=%s)", SEASON_EXTERNAL_ID, season_id)
    else:
        # Fetch season coverage to get start/end dates.
        seasons = await provider.get_seasons(COMPETITION_ID)
        api_season = next((s for s in seasons if s.get("year") == SEASON_YEAR), None)
        start_date = _parse_date(api_season.get("start")) if api_season else None
        end_date = _parse_date(api_season.get("end")) if api_season else None

        async with async_session() as session:
            season = Season(
                competition_id=competition.id,
                label=SEASON_LABEL,
                start_date=start_date,
                end_date=end_date,
                availability_status="imported",
            )
            session.add(season)
            await session.flush()
            season_id = season.id

            ext = ExternalId(
                entity_type="season",
                provider="api_football",
                external_id=SEASON_EXTERNAL_ID,
                competition_id=competition.id,
                season_id=season_id,
            )
            session.add(ext)
            await session.commit()
        logger.info("Created season id=%s label=%r", season_id, SEASON_LABEL)

    # 3. Fetch standings from API-Football.
    logger.info("Fetching standings for league=%s season=%s", COMPETITION_ID, SEASON_YEAR)
    rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
    logger.info("API returned %s standings rows", len(rows_raw))

    # 4. Create or reuse StandingSnapshot.
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

    # 5. Persist StandingRows.
    created_rows = 0
    reused_rows = 0
    skipped = 0
    for api_row in rows_raw:
        api_team = api_row.get("team", {})
        api_team_id = api_team.get("id")
        if api_team_id is None:
            logger.warning("Skipping row with no team id")
            skipped += 1
            continue

        repo = Repository(Team)
        existing_team = await repo.get_by_external_id(
            provider="api_football",
            external_id=str(api_team_id),
            entity_type="team",
        )
        if existing_team is None:
            logger.warning("Team %s not in DB — skipping", api_team_id)
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
                sr = ApiFootballAdapters.standing_row(api_row)
                existing_row.form = ",".join(sr.form) if isinstance(sr.form, list) else str(sr.form or "")
                await session.commit()
                reused_rows += 1
                continue

            sr = ApiFootballAdapters.standing_row(api_row)
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
                form=",".join(sr.form) if isinstance(sr.form, list) else str(sr.form or ""),
            )
            session.add(row)
            await session.commit()
            created_rows += 1

    logger.info("Persistence: created=%s already_present=%s skipped=%s", created_rows, reused_rows, skipped)

    # 6. Read back and verify.
    async with async_session() as session:
        result = await session.execute(
            select(StandingRow)
            .where(StandingRow.standing_snapshot_id == snapshot_id)
            .order_by(StandingRow.position)
        )
        stored_rows = list(result.scalars().all())

    logger.info("Read-back: %s standing rows in Neon", len(stored_rows))
    for row in stored_rows[:5]:
        async with async_session() as session:
            team = await session.get(Team, row.team_id)
        logger.info("  pos=%2s team=%-22s P=%2s W=%2s D=%2s L=%2s GF=%3s GA=%3s GD=%+3s pts=%2s",
                    row.position, team.name if team else "?", row.played, row.won,
                    row.drawn, row.lost, row.goals_for, row.goals_against,
                    row.goal_difference, row.points)

    # 7. Final assertions.
    assert len(stored_rows) > 0, "no rows persisted"
    assert stored_rows[0].position == 1, "top position mismatch"
    logger.info("Verification passed: %s rows persisted/reused, %s read back.", created_rows + reused_rows, len(stored_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
