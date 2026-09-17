"""Alembic env.py."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.config import DATABASE_URL_SYNC

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL_SYNC)

from db.base import Base
target_metadata = Base.metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.QueuePool,
    )
    with connectable.connect() as connection:
        connection.run_sync(do_run_migrations)


def do_run_migrations(connection):
    Base.metadata.create_all(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
