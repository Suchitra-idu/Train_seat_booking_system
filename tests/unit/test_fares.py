"""Fares are money, exact integer minor units, deterministic rounding. Where a
sourced figure exists (seat61 / SLR, PLAN §7) we assert against it as an oracle, not
against our own arithmetic. Rates, class and demand multipliers are all parameters
(D11): nothing here is hardcoded to Sri Lanka.
"""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from slr.domain.fares import Money, demand_multiplier, distance_fare, dynamic_fare


@pytest.mark.unit
def test_money_is_exact_minor_units():
    assert Money.rupees(1200).cents == 120_000
    assert Money(120_000) + Money(500) == Money(120_500)
    assert Money(100) * 3 == Money(300)
    assert Money(100) < Money(101)


# ── oracle: the Kandy leg (PLAN §7) ───────────────────────────────────────────
# Colombo Fort→Kandy 2nd-class reserved is a sourced Rs 1,200 (seat61) over ~120 km.
# At Rs 10.00/km that reproduces exactly, a hand-checkable reference point.


@pytest.mark.unit
def test_distance_fare_reproduces_the_sourced_kandy_fare():
    fare = distance_fare(distance_km=120.0, rate_per_km=Money.rupees(10), class_mult=1.0)
    assert fare == Money.rupees(1200)


@pytest.mark.unit
def test_class_multiplier_scales_the_base():
    base = distance_fare(120.0, Money.rupees(10), class_mult=1.0)
    first = distance_fare(120.0, Money.rupees(10), class_mult=1.5)
    assert base == Money.rupees(1200)
    assert first == Money.rupees(1800)


@pytest.mark.unit
def test_rounding_is_half_up_to_the_cent():
    # 200020 cents * 1.005 = 201020.1 -> 201020 (half-up, deterministic)
    fare = distance_fare(292.0, Money(685), class_mult=1.005)
    assert fare == Money(201_020)


# ── demand multiplier ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_demand_multiplier_endpoints_and_clamping():
    assert demand_multiplier(0.0, floor=1.0, ceiling=1.8) == pytest.approx(1.0)
    assert demand_multiplier(1.0, floor=1.0, ceiling=1.8) == pytest.approx(1.8)
    assert demand_multiplier(0.5, floor=1.0, ceiling=1.8) == pytest.approx(1.4)
    # occupancy outside [0,1] clamps rather than extrapolating
    assert demand_multiplier(-0.3, floor=1.0, ceiling=1.8) == pytest.approx(1.0)
    assert demand_multiplier(2.0, floor=1.0, ceiling=1.8) == pytest.approx(1.8)


@pytest.mark.unit
def test_demand_multiplier_rejects_inverted_band():
    with pytest.raises(ValueError):
        demand_multiplier(0.5, floor=1.8, ceiling=1.0)


# ── dynamic fare = distance fare * demand ─────────────────────────────────────


@pytest.mark.unit
def test_dynamic_fare_at_zero_occupancy_equals_base():
    base = distance_fare(120.0, Money.rupees(10), 1.0)
    dyn = dynamic_fare(120.0, Money.rupees(10), 1.0, occupancy=0.0, floor=1.0, ceiling=1.8)
    assert dyn == base


@pytest.mark.unit
def test_dynamic_fare_at_full_occupancy_hits_the_ceiling():
    dyn = dynamic_fare(120.0, Money.rupees(10), 1.0, occupancy=1.0, floor=1.0, ceiling=1.8)
    assert dyn == Money.rupees(2160)  # 1200 * 1.8


@pytest.mark.unit
@given(
    distance=st.floats(min_value=1, max_value=300),
    rate=st.integers(min_value=1, max_value=5000),
    occ_lo=st.floats(min_value=0, max_value=1),
    occ_hi=st.floats(min_value=0, max_value=1),
)
def test_dynamic_fare_is_monotonic_in_occupancy(distance, rate, occ_lo, occ_hi):
    assume(occ_lo <= occ_hi)
    lo = dynamic_fare(distance, Money(rate), 1.0, occupancy=occ_lo, floor=1.0, ceiling=2.0)
    hi = dynamic_fare(distance, Money(rate), 1.0, occupancy=occ_hi, floor=1.0, ceiling=2.0)
    assert lo.cents <= hi.cents


@pytest.mark.unit
@given(
    d_lo=st.floats(min_value=1, max_value=300),
    d_hi=st.floats(min_value=1, max_value=300),
    rate=st.integers(min_value=1, max_value=5000),
)
def test_distance_fare_is_monotonic_in_distance(d_lo, d_hi, rate):
    assume(d_lo <= d_hi)
    assert (
        distance_fare(d_lo, Money(rate), 1.0).cents
        <= distance_fare(d_hi, Money(rate), 1.0).cents
    )
