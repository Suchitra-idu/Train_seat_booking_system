"""Fare-strategy conformance. price returns non-negative Money, deterministically."""

import pytest

from slr.adapters.fixed_fare import FixedFare
from slr.domain.fares import Money


@pytest.fixture
def strategy():
    return FixedFare(Money.rupees(500))


@pytest.mark.integration
def test_price_returns_money(strategy):
    price = strategy.price(distance_km=120.0, class_mult=1.0, occupancy=0.5)
    assert isinstance(price, Money)
    assert price.cents >= 0


@pytest.mark.integration
def test_price_is_deterministic_for_the_same_inputs(strategy):
    a = strategy.price(distance_km=120.0, class_mult=1.5, occupancy=0.2)
    b = strategy.price(distance_km=120.0, class_mult=1.5, occupancy=0.2)
    assert a == b
