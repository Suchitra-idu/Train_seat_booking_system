"""The seat-packing optimizer (D10): pure interval partitioning, two uses —
(1) assign a leg to the seat that best preserves long contiguous availability,
(2) quantify seat-km unlocked vs rigid whole-journey booking (the impact metric).

Interval-graph colouring has a known optimum (max overlap depth), so we oracle-test
against a brute-force depth count and assert the greedy result is never worse.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from slr.domain.packing import choose_seat, impact_seat_km, min_seats, pack
from slr.domain.stations import Leg, Station, km_index

MAX_SEQ = 30


def legs():
    return st.integers(min_value=0, max_value=MAX_SEQ - 1).flatmap(
        lambda o: st.integers(min_value=o + 1, max_value=MAX_SEQ).map(lambda d: Leg(o, d))
    )


def leg_sets():
    return st.lists(legs(), min_size=0, max_size=12)


def _max_overlap_depth(ls) -> int:
    if not ls:
        return 0
    return max(sum(leg.contains(p) for leg in ls) for p in range(MAX_SEQ + 1))


# ── min_seats == max overlap depth (the optimum) ──────────────────────────────


@pytest.mark.unit
@given(leg_sets())
def test_min_seats_equals_max_overlap_depth(ls):
    assert min_seats(ls) == _max_overlap_depth(ls)


@pytest.mark.unit
def test_adjacent_legs_share_one_seat():
    assert min_seats([Leg(0, 5), Leg(5, 12)]) == 1  # resale: same seat


@pytest.mark.unit
def test_fully_overlapping_legs_need_one_seat_each():
    assert min_seats([Leg(0, 10), Leg(0, 10), Leg(0, 10)]) == 3


# ── pack: a valid, optimal colouring ──────────────────────────────────────────


@pytest.mark.unit
@given(leg_sets())
def test_pack_assigns_every_leg(ls):
    assignment = pack(ls)
    assert len(assignment) == len(ls)


@pytest.mark.unit
@given(leg_sets())
def test_pack_never_puts_overlapping_legs_on_one_seat(ls):
    assignment = pack(ls)
    by_seat: dict[int, list[Leg]] = {}
    for leg, seat in zip(ls, assignment, strict=True):
        by_seat.setdefault(seat, []).append(leg)
    for seat_legs in by_seat.values():
        for i in range(len(seat_legs)):
            for j in range(i + 1, len(seat_legs)):
                assert not seat_legs[i].overlaps(seat_legs[j])


@pytest.mark.unit
@given(leg_sets())
def test_pack_uses_exactly_the_optimum_number_of_seats(ls):
    assignment = pack(ls)
    used = len(set(assignment))
    assert used == min_seats(ls)
    assert used <= len(ls)  # never worse than the naive one-seat-per-leg


# ── choose_seat: preserve contiguity, never overlap ───────────────────────────


@pytest.mark.unit
def test_choose_seat_rejects_when_no_seat_is_free():
    seats = [[Leg(0, 10)]]  # the only seat is busy across the whole span
    assert choose_seat(seats, Leg(2, 6)) is None


@pytest.mark.unit
def test_choose_seat_prefers_extending_a_fuller_feasible_seat():
    # seat 0 already carries [0,5); seat 1 is empty. Leg [5,10) fits on both
    # (adjacent to seat 0). Best-fit consolidates onto seat 0, leaving seat 1 fully free.
    seats = [[Leg(0, 5)], []]
    assert choose_seat(seats, Leg(5, 10)) == 0


@pytest.mark.unit
def test_choose_seat_skips_the_overlapping_seat():
    seats = [[Leg(0, 6)], []]  # seat 0 overlaps [2,4); only seat 1 is feasible
    assert choose_seat(seats, Leg(2, 4)) == 1


# ── impact metric: seat-km reclaimed vs whole-journey ─────────────────────────


@pytest.mark.unit
def test_impact_reclaims_the_stranded_kandy_km():
    # Fort(0km)…Kandy(121km)…Badulla(292km). A whole-journey Kandy booking strands
    # 292-121 = 171 resellable km — the sourced figure from PLAN §7.
    stations = [Station("CF", "Fort", 0, 0.0), Station("KDY", "Kandy", 5, 121.0),
                Station("BAD", "Badulla", 12, 292.0)]
    idx = km_index(stations)
    assert impact_seat_km([Leg(0, 5)], idx, route_km=292.0) == pytest.approx(171.0)


@pytest.mark.unit
def test_a_whole_route_leg_strands_nothing():
    stations = [Station("CF", "Fort", 0, 0.0), Station("BAD", "Badulla", 12, 292.0)]
    idx = km_index(stations)
    assert impact_seat_km([Leg(0, 12)], idx, route_km=292.0) == pytest.approx(0.0)
