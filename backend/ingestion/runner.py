from __future__ import annotations

from typing import Any

from db.session import async_session
from ingestion.fixtures import ingest_fixtures


async def run_fixture_ingestion(
    provider_name: str,
    competition_id: int,
    season_id: int,
    data_source_id: int,
    season_year: int | None = None,
    *,
    session_factory: Any = None,
) -> Any:
    factory = session_factory if session_factory is not None else async_session
    async with factory() as session:
        try:
            result = await ingest_fixtures(
                session,
                provider_name=provider_name,
                competition_id=competition_id,
                season_id=season_id,
                data_source_id=data_source_id,
                season_year=season_year,
            )
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
