"""Shared fixtures for the integration tier. The Postgres container is started once per
session and skipped cleanly when Docker is unavailable, so the fake-backed tests still run.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from slr.adapters.orm import create_schema


@pytest.fixture(scope="session")
def postgres_engine():
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        try:
            from testcontainers.postgres import PostgresContainer
        except ImportError:
            pytest.skip("testcontainers not installed")
    try:
        container = PostgresContainer("postgres:16-alpine", driver="psycopg")
        container.start()
    except Exception as exc:
        pytest.skip(f"docker unavailable: {exc}")
    engine = create_engine(container.get_connection_url(), pool_size=20, max_overflow=10)
    try:
        create_schema(engine)
        yield engine
    finally:
        engine.dispose()
        container.stop()


@pytest.fixture
def pg_session_factory(postgres_engine):
    with postgres_engine.begin() as conn:
        conn.execute(text("TRUNCATE booking, waitlist, trip"))
    return sessionmaker(bind=postgres_engine)
