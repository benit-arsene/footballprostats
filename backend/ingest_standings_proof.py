"""Proof-of-pipeline: fetch EPL 2024 standings from API-Football,
normalize them, persist them to Neon, and read them back.

Usage:
    cd backend && python ingest_standings_proof.py
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
logger = logging.getLogger("ingest_standings_proof")

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


COMPETITION_ID = 39  # Premier League
SEASON_YEAR = int(os.getenv("SEASON_YEAR", "2024"))
SNAPSHOT_LABEL = f"EPL {SEASON_YEAR}/{SEASON_YEAR + 1} Final Standings"


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
    logger.info("Resolved competition: internal_id=%s name=%r",
                competition.id, competition.name)

    # 2. Resolve the existing 2024/2025 Season from Neon.
    async with async_session() as session:
        season_result = await session.execute(select(Season))
        season = next(
            (s for s in season_result.scalars().all()
             if s.label == f"{SEASON_YEAR}/{SEASON_YEAR + 1}"),
            None,
        )
    if season is None:
        logger.error("No Season row with label '2024/2025' found in Neon")
        return 1
    logger.info("Resolved season: internal_id=%s label=%r",
                season.id, season.label)

    # 3. Fetch the standings (single API request).
    logger.info("Fetching standings for league=%s season=%s", COMPETITION_ID, SEASON_YEAR)
    rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
    logger.info("API returned %s standings rows", len(rows_raw))

    # 4. Create or reuse the StandingSnapshot for this season.
    async with async_session() as session:
        snap_result = await session.execute(
            select(StandingSnapshot).where(
                StandingSnapshot.season_id == season.id,
                StandingSnapshot.label == SNAPSHOT_LABEL,
            )
        )
        snapshot = snap_result.scalar_one_or_none()
        if snapshot is None:
            snapshot = StandingSnapshot(
                season_id=season.id,
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
    logger.info("StandingSnapshot %s (id=%s)",
                "created" if created_snapshot else "already present",
                snapshot_id)

    # 5. Persist each StandingRow, resolving team_id via external_ids.
    created_rows = 0
    reused_rows = 0
    for api_row in rows_raw:
        api_team = api_row.get("team", {})
        api_team_id = api_team.get("id")
        if api_team_id is None:
            logger.warning("Skipping row with no team id")
            continue

        # Resolve internal team id via external_ids.
        repo = Repository(Team)
        existing_team = await repo.get_by_external_id(
            provider="api_football",
            external_id=str(api_team_id),
            entity_type="team",
        )
        if existing_team is None:
            logger.warning("Team %s not in DB — skipping", api_team_id)
            continue
        internal_team_id = existing_team["team_id"]

        # Check for existing row.
        async with async_session() as session:
            row_result = await session.execute(
                select(StandingRow).where(
                    StandingRow.standing_snapshot_id == snapshot_id,
                    StandingRow.team_id == internal_team_id,
                )
            )
            existing_row = row_result.scalar_one_or_none()
            if existing_row is not None:
                # Update form field in case it was stored incorrectly before
                sr = ApiFootballAdapters.standing_row(api_row)
                existing_row.form = ",".join(sr.form) if isinstance(sr.form, list) else str(sr.form or "")
                await session.commit()
                reused_rows += 1
                logger.info("  already present (form updated): team=%s pos=%s pts=%s",
                            api_team.get("name"), existing_row.position,
                            existing_row.points)
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
            logger.info("  created: team=%s pos=%s pts=%s",
                        api_team.get("name"), sr.position, sr.points)

    logger.info("Persistence: created=%s already_present=%s", created_rows, reused_rows)

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
    if len(stored_rows) > 5:
        logger.info("  ... (%s more rows)", len(stored_rows) - 5)

    # 7. Final assertions.
    assert created_rows + reused_rows == len(rows_raw), "row count mismatch"
    assert len(stored_rows) == len(rows_raw), "read-back count mismatch"
    assert stored_rows[0].position == 1, "top position mismatch"
    logger.info("Verification passed: %s rows persisted/reused, %s read back.",
                created_rows + reused_rows, len(stored_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))