"""Contract-tier fixtures: the HTTP app on an all-fake Container, so every route is
exercised with zero infrastructure. The seeded trip mirrors the use-case test trip.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.integration.usecases._helpers import make_trip

from slr.app.config import Settings
from slr.app.main import create_app
from slr.app.wiring import wire_fake

COUNTER_KEY = "test-counter-key"


def _settings() -> Settings:
    return Settings(
        database_url="fake",
        counter_key=COUNTER_KEY,
        currency="LKR",
        fare_strategy="dynamic",
        fare_rate_per_km_cents=685,
        policy={},
    )


@pytest.fixture
def client() -> TestClient:
    container = wire_fake((make_trip(),))
    return TestClient(create_app(container=container, settings=_settings()))
