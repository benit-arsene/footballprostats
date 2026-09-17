"""Database configuration for FootballProStats."""

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://footballprostats:footballprostats@localhost:5432/footballprostats",
)

DATABASE_URL_SYNC = DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql://", 1
)

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
