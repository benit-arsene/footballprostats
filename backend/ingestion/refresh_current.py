"""Production entrypoint: refresh current-season Premier League data.

Fetches current-season standings (and fixtures count) from football-data.org,
persists standings idempotently to Neon, and exits with a meaningful status.

Usage:
    cd backend && python -m ingestion.refresh_current
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("refresh_current")

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
from providers.factory import build_provider_registry  # noqa: E402
from providers.football_data.adapters import FootballDataAdapters  # noqa: E402
from providers.routing import route_provider  # noqa: E402


COMPETITION_ID = 39
SEASON_YEAR = get_season_year()
SEASON_LABEL = f"{SEASON_YEAR}/{SEASON_YEAR + 1}"
SEASON_EXTERNAL_ID = f"PL/{SEASON_YEAR}"
SNAPSHOT_LABEL = f"EPL {SEASON_LABEL} football-data.org standings"


async def _resolve_competition(session):
    result = await session.execute(select(Competition))
    return next((c for c in result.scalars().all() if c.name == "Premier League"), None)


async def _resolve_or_create_season(session, competition):
    repo = Repository(Season)
    existing = await repo.get_by_external_id(
        provider="football_data", external_id=SEASON_EXTERNAL_ID, entity_type="season"
    )
    if existing is not None:
        return existing["season_id"]
    season = Season(
        competition_id=competition.id,
        label=SEASON_LABEL,
        availability_status="imported",
    )
    session.add(season)
    await session.flush()
    sid = season.id
    ext = ExternalId(
        entity_type="season",
        provider="football_data",
        external_id=SEASON_EXTERNAL_ID,
        competition_id=competition.id,
        season_id=sid,
    )
    session.add(ext)
    await session.commit()
    return sid


async def run() -> int:
    registry = build_provider_registry()
    available = set(registry.list_providers())
    if "football_data" not in available:
        logger.error("football_data provider not registered (missing FOOTBALLDATA_KEY)")
        return 1

    name = route_provider("standings", season_label=SEASON_LABEL, data_type="standings",
                          available_providers=available)
    if name != "football_data":
        logger.error("Routing selected %s instead of football_data", name)
        return 1

    provider = registry.get_provider("football_data")

    try:
        async with async_session() as session:
            competition = await _resolve_competition(session)
            if competition is None:
                logger.error("No Premier League competition found")
                return 1
            season_id = await _resolve_or_create_season(session, competition)

        # Fetch standings.
        rows_raw = await provider.get_standings(COMPETITION_ID, SEASON_YEAR)
        logger.info("Fetched %s standings rows from football-data.org", len(rows_raw))

        # Fetch fixtures count (lightweight, respects quota).
        try:
            fixtures = await provider.get_fixtures(league_id=COMPETITION_ID, season=SEASON_YEAR)
            logger.info("Fetched %s fixtures from football-data.org", len(fixtures))
        except Exception as e:
            logger.warning("Fixtures fetch failed (non-fatal): %s", e)

        if not rows_raw:
            logger.warning("No standings rows returned; preserving existing data")
            return 0

        # Persist.
        async with async_session() as session:
            snap_result = await session.execute(
                select(StandingSnapshot).where(
                    StandingSnapshot.season_id == season_id,
                    StandingSnapshot.label == SNAPSHOT_LABEL,
                )
            )
            snapshot = snap_result.scalar_one_or_none()
            created_snapshot = False
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
            snapshot_id = snapshot.id
            await session.commit()

        created = 0
        reused = 0
        skipped = 0
        for api_row in rows_raw:
            ts = FootballDataAdapters.team_summary(api_row.get("team", {}))
            fd_id = str(ts.id)
            repo = Repository(Team)
            existing_team = await repo.get_by_external_id(
                provider="football_data", external_id=fd_id, entity_type="team"
            )
            if existing_team is None:
                logger.warning("No team mapping for fd_id=%s (%s) — skipping", fd_id, ts.name)
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
                if row_result.scalar_one_or_none() is not None:
                    reused += 1
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
                created += 1

        logger.info("Standings persistence: created=%s reused=%s skipped=%s", created, reused, skipped)

        # If nothing persisted and snapshot was newly created, remove it.
        if created + reused == 0 and created_snapshot:
            async with async_session() as session:
                snap = await session.get(StandingSnapshot, snapshot_id)
                if snap is not None:
                    await session.delete(snap)
                    await session.commit()
            logger.warning("Removed empty snapshot %s", snapshot_id)

        if skipped > 0:
            logger.warning("%s teams skipped (missing mappings)", skipped)

        return 0

    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
