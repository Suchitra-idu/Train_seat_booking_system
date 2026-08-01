"""Fare-strategy conformance. price returns non-negative Money, deterministically, across
the fixed fake and both real strategies.
"""

import pytest

from slr.adapters.distance_fare import DistanceFare
from slr.adapters.dynamic_fare import DynamicFare
from slr.adapters.fixed_fare import FixedFare
from slr.domain.fares import Money


@pytest.fixture(params=["fixed", "distance", "dynamic"])
def strategy(request):
    rate = Money.rupees(10)
    return {
        "fixed": FixedFare(Money.rupees(500)),
        "distance": DistanceFare(rate),
        "dynamic": DynamicFare(rate),
    }[request.param]


@pytest.mark.integration
def test_price_returns_non_negative_money(strategy):
    price = strategy.price(distance_km=120.0, class_mult=1.0, occupancy=0.5)
    assert isinstance(price, Money)
    assert price.cents >= 0


@pytest.mark.integration
def test_price_is_deterministic_for_the_same_inputs(strategy):
    a = strategy.price(distance_km=120.0, class_mult=1.5, occupancy=0.2)
    b = strategy.price(distance_km=120.0, class_mult=1.5, occupancy=0.2)
    assert a == b


@pytest.mark.integration
def test_distance_fare_reproduces_the_kandy_oracle():
    price = DistanceFare(Money.rupees(10)).price(
        distance_km=120.0, class_mult=1.0, occupancy=0.9
    )
    assert price == Money.rupees(1200)


@pytest.mark.integration
def test_dynamic_fare_rises_with_occupancy():
    strategy = DynamicFare(Money.rupees(10), floor=1.0, ceiling=1.8)
    low = strategy.price(distance_km=120.0, class_mult=1.0, occupancy=0.0)
    high = strategy.price(distance_km=120.0, class_mult=1.0, occupancy=1.0)
    assert high.cents > low.cents
