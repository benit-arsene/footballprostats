"""Idempotent registration of La Liga using football-data.org competition code PD."""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.season import Season
from db.session import async_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("register_laliga")

COMPETITION_NAME = "La Liga"
COMPETITION_SLUG = "laliga"
COMPETITION_COUNTRY = "Spain"
PROVIDER = "football_data"
EXTERNAL_ID = "PD"
SEASON_LABEL = "2026/2027"
SEASON_START = datetime(2026, 8, 16)
SEASON_END = datetime(2027, 5, 30)


class RegistrationError(Exception):
    pass


async def main() -> int:
    async with async_session() as session:
        try:
            async with session.begin():
                slug_result = await session.execute(
                    select(Competition).where(Competition.slug == COMPETITION_SLUG)
                )
                slug_competition = slug_result.scalar_one_or_none()

                ext_result = await session.execute(
                    select(ExternalId).where(
                        ExternalId.entity_type == "competition",
                        ExternalId.provider == PROVIDER,
                        ExternalId.external_id == EXTERNAL_ID,
                    )
                )
                ext = ext_result.scalar_one_or_none()

                mapped_competition = None
                if ext is not None and ext.competition_id is not None:
                    mapped_result = await session.execute(
                        select(Competition).where(Competition.id == ext.competition_id)
                    )
                    mapped_competition = mapped_result.scalar_one_or_none()

                if slug_competition is not None and mapped_competition is not None and slug_competition.id != mapped_competition.id:
                    raise RegistrationError("slug and external-id mapping point to different competitions")

                competition = slug_competition or mapped_competition
                if competition is None:
                    competition = Competition(
                        name=COMPETITION_NAME,
                        slug=COMPETITION_SLUG,
                        country=COMPETITION_COUNTRY,
                        logo_url=None,
                    )
                    session.add(competition)
                    await session.flush()
                else:
                    if competition.name != COMPETITION_NAME or competition.slug != COMPETITION_SLUG or competition.country != COMPETITION_COUNTRY:
                        raise RegistrationError("existing competition conflicts with intended La Liga registration")

                if ext is None:
                    ext = ExternalId(
                        entity_type="competition",
                        provider=PROVIDER,
                        external_id=EXTERNAL_ID,
                        competition_id=competition.id,
                    )
                    session.add(ext)
                else:
                    if ext.competition_id is None:
                        ext.competition_id = competition.id
                    elif ext.competition_id != competition.id:
                        raise RegistrationError("external-id mapping points to a different competition")

                season_result = await session.execute(
                    select(Season).where(
                        Season.competition_id == competition.id,
                        Season.label == SEASON_LABEL,
                    )
                )
                season = season_result.scalar_one_or_none()
                if season is None:
                    season = Season(
                        competition_id=competition.id,
                        label=SEASON_LABEL,
                        start_date=SEASON_START,
                        end_date=SEASON_END,
                        availability_status="not_imported",
                    )
                    session.add(season)
                else:
                    if season.start_date != SEASON_START or season.end_date != SEASON_END:
                        raise RegistrationError("existing season conflicts with intended La Liga registration")

                logger.info("La Liga registration verified/created (competition_id=%s)", competition.id)
        except RegistrationError as exc:
            logger.error("La Liga registration aborted: %s", exc)
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))