"""Interval math is the load-bearing correctness core (D2): occupancy is a set of
half-open station intervals [origin, dest), and 'two legs share a seat' is exactly
'their intervals do not overlap'. These properties are what the DB EXCLUDE constraint
enforces later — proven here, cheaply, first.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from slr.domain.errors import InvalidLeg
from slr.domain.stations import Leg, Station, km_index

MAX_SEQ = 40


def legs(min_seq: int = 0, max_seq: int = MAX_SEQ):
    return st.integers(min_value=min_seq, max_value=max_seq - 1).flatmap(
        lambda o: st.integers(min_value=o + 1, max_value=max_seq).map(
            lambda d: Leg(o, d)
        )
    )


def _resellable_on_one_seat(a: Leg, b: Leg) -> bool:
    """Domain truth: a seat can serve both legs iff their intervals are disjoint."""
    return not a.overlaps(b)


# ── construction / validation (hostile input fails loud, D-doctrine) ──────────


@pytest.mark.unit
@pytest.mark.parametrize("origin,dest", [(3, 3), (5, 2), (0, 0), (10, 9)])
def test_empty_or_reversed_leg_is_rejected(origin, dest):
    with pytest.raises(InvalidLeg):
        Leg(origin, dest)


@pytest.mark.unit
def test_negative_sequence_is_rejected():
    with pytest.raises(InvalidLeg):
        Leg(-1, 3)


@pytest.mark.unit
@given(legs())
def test_a_valid_leg_has_positive_length(leg):
    assert leg.length >= 1
    assert leg.length == leg.dest_seq - leg.origin_seq


# ── overlap algebra ───────────────────────────────────────────────────────────


@pytest.mark.unit
@given(legs(), legs())
def test_overlap_is_symmetric(a, b):
    assert a.overlaps(b) == b.overlaps(a)


@pytest.mark.unit
@given(legs())
def test_overlap_is_reflexive(a):
    assert a.overlaps(a)


@pytest.mark.unit
@given(legs(), legs())
def test_adjacent_legs_never_overlap(a, b):
    if a.is_adjacent(b):
        assert not a.overlaps(b)


@pytest.mark.unit
def test_adjacency_is_the_resale_signature():
    # [A,B) then [B,C) on the SAME seat — the journey the whole system exists for.
    fort_kandy = Leg(0, 5)
    kandy_badulla = Leg(5, 12)
    assert fort_kandy.is_adjacent(kandy_badulla)
    assert _resellable_on_one_seat(fort_kandy, kandy_badulla)


@pytest.mark.unit
@given(legs(), legs())
def test_no_overlap_iff_resellable(a, b):
    assert _resellable_on_one_seat(a, b) == (not a.overlaps(b))


@pytest.mark.unit
@given(legs(), legs())
def test_overlap_matches_shared_interior_point(a, b):
    shares_point = any(a.contains(s) and b.contains(s) for s in range(MAX_SEQ + 1))
    assert a.overlaps(b) == shares_point


# ── contains ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
@given(legs())
def test_contains_is_half_open(leg):
    assert leg.contains(leg.origin_seq)
    assert not leg.contains(leg.dest_seq)  # half-open: dest excluded
    assert not leg.contains(leg.origin_seq - 1)


# ── distance in km ────────────────────────────────────────────────────────────


def _monotonic_km(n: int):
    return st.lists(
        st.integers(min_value=1, max_value=30), min_size=n, max_size=n
    ).map(lambda steps: [sum(steps[:i]) for i in range(n + 1)])


@pytest.mark.unit
@given(_monotonic_km(MAX_SEQ))
def test_distance_is_positive_and_additive_over_adjacent_legs(km):
    idx = km_index([Station(f"S{i}", f"Station {i}", i, km[i]) for i in range(len(km))])
    a, b, c = 3, 9, 15
    left, right, whole = Leg(a, b), Leg(b, c), Leg(a, c)
    assert left.distance_km(idx) > 0
    assert whole.distance_km(idx) == pytest.approx(
        left.distance_km(idx) + right.distance_km(idx)
    )


@pytest.mark.unit
def test_km_index_maps_sequence_to_km():
    stations = [Station("CF", "Colombo Fort", 0, 0.0), Station("KDY", "Kandy", 5, 120.5)]
    idx = km_index(stations)
    assert idx[0] == 0.0
    assert idx[5] == 120.5
