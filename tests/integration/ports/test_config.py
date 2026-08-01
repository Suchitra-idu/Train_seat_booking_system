"""Config conformance. Typed reads. A missing key raises KeyError."""

import pytest

from slr.adapters.fixture_config import FixtureConfig


@pytest.fixture
def config():
    return FixtureConfig(
        {"hold_ttl_seconds": 600, "rate_per_km_cents": "1000", "route_code": "CMB-BAD"}
    )


@pytest.mark.integration
def test_typed_reads(config):
    assert config.get_int("hold_ttl_seconds") == 600
    assert config.get_int("rate_per_km_cents") == 1000
    assert config.get_float("hold_ttl_seconds") == 600.0
    assert config.get_str("route_code") == "CMB-BAD"


@pytest.mark.integration
def test_missing_key_raises(config):
    with pytest.raises(KeyError):
        config.get_int("does_not_exist")
