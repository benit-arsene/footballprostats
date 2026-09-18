"""Database configuration for FootballProStats."""

import os
import re
from urllib.parse import urlparse, parse_qsl, urlencode

_ENV_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://footballprostats:footballprostats@localhost:5432/footballprostats",
)


def _derive_urls(raw: str):
    parsed = urlparse(raw)
    query_params = dict(parse_qsl(parsed.query))

    has_ssl = "sslmode" in query_params or "sslmode" in raw

    pg_sync = parsed._replace(scheme="postgresql")
    pg_sync_query = {k: v for k, v in query_params.items() if k != "channel_binding"}
    sync_url = pg_sync._replace(query=urlencode(pg_sync_query)).geturl()

    pg_async = parsed._replace(scheme="postgresql+asyncpg")
    async_query = {k: v for k, v in query_params.items() if k not in ("sslmode", "channel_binding")}
    async_url = pg_async._replace(query=urlencode(async_query)).geturl()

    return async_url, sync_url, has_ssl


DATABASE_URL, DATABASE_URL_SYNC, HAS_SSL = _derive_urls(_ENV_URL)

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
