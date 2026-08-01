"""The Alembic migration builds the overlap invariant on a clean database (D19). Proves
the compose bring-up path, separate from the create_schema path the other tests use.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

_MIGRATIONS = Path(__file__).resolve().parents[2] / "backend" / "slr" / "app" / "migrations"


@pytest.mark.integration
def test_migration_creates_the_overlap_constraint(postgres_engine):
    target = postgres_engine.url.set(database="alembic_check")
    admin = postgres_engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        admin.execute(text("DROP DATABASE IF EXISTS alembic_check WITH (FORCE)"))
        admin.execute(text("CREATE DATABASE alembic_check"))
    finally:
        admin.close()

    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS))
    cfg.set_main_option("sqlalchemy.url", target.render_as_string(hide_password=False))
    command.upgrade(cfg, "head")

    engine = create_engine(target)
    try:
        with engine.connect() as conn:
            found = conn.execute(
                text("SELECT conname FROM pg_constraint WHERE conname = 'booking_no_overlap'")
            ).scalar()
    finally:
        engine.dispose()
    assert found == "booking_no_overlap"
