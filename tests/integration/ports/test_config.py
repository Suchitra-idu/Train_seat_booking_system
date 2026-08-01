"""Config conformance. Typed reads; a missing key raises KeyError, for fake and real."""

import pytest

from slr.adapters.env_config import EnvConfig
from slr.adapters.fixture_config import FixtureConfig

VALUES = {"hold_ttl_seconds": "600", "rate_per_km_cents": "1000", "route_code": "CMB-BAD"}


@pytest.fixture(params=["fake", "real"])
def config(request):
    return FixtureConfig(VALUES) if request.param == "fake" else EnvConfig(VALUES)


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
