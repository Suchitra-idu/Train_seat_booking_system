"""Alembic online migration runner. The URL comes from config or DATABASE_URL (D11)."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from slr.adapters.orm import Base

config = context.config
url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")
if url:
    config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
