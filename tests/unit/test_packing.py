"""The seat-packing optimizer (D10): pure interval partitioning, two uses,
(1) assign a leg to the seat that best preserves long contiguous availability,
(2) quantify seat-km unlocked vs rigid whole-journey booking (the impact metric).

Interval-graph colouring has a known optimum (max overlap depth), so we oracle-test
against a brute-force depth count and assert the greedy result is never worse.
"""

import itertools

import pytest
from hypothesis import given
from hypothesis import strategies as st

from slr.domain.packing import (
    SeatOffer,
    choose_seat,
    impact_seat_km,
    min_seats,
    pack,
    predict_standing_seats,
)
from slr.domain.stations import Leg, Station, km_index

MAX_SEQ = 30


def legs():
    return st.integers(min_value=0, max_value=MAX_SEQ - 1).flatmap(
        lambda o: st.integers(min_value=o + 1, max_value=MAX_SEQ).map(lambda d: Leg(o, d))
    )


def leg_sets():
    return st.lists(legs(), min_size=0, max_size=12)


@st.composite
def disjoint_legs(draw):
    """One seat's real occupancy: pairwise non-overlapping legs (the repo invariant)."""
    cuts = sorted(draw(st.sets(st.integers(min_value=0, max_value=MAX_SEQ), max_size=8)))
    spans = [Leg(a, b) for a, b in itertools.pairwise(cuts)]
    return [leg for leg in spans if draw(st.booleans())]


def seat_sets():
    return st.lists(disjoint_legs(), min_size=0, max_size=4)


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
    # 292-121 = 171 resellable km, the sourced figure from PLAN §7.
    stations = [Station("CF", "Fort", 0, 0.0), Station("KDY", "Kandy", 5, 121.0),
                Station("BAD", "Badulla", 12, 292.0)]
    idx = km_index(stations)
    assert impact_seat_km([Leg(0, 5)], idx, route_km=292.0) == pytest.approx(171.0)


@pytest.mark.unit
def test_a_whole_route_leg_strands_nothing():
    stations = [Station("CF", "Fort", 0, 0.0), Station("BAD", "Badulla", 12, 292.0)]
    idx = km_index(stations)
    assert impact_seat_km([Leg(0, 12)], idx, route_km=292.0) == pytest.approx(0.0)


# ── standing overflow: earliest-seat-at-station, FIFO (D20) ────────────────────


@pytest.mark.unit
def test_standing_sits_immediately_when_a_seat_is_free_all_the_way():
    # an empty seat serves the whole leg. They board at their origin.
    assert predict_standing_seats([[]], [Leg(0, 5)]) == [SeatOffer(0, 0)]


@pytest.mark.unit
def test_standing_sits_after_the_occupant_alights():
    # seat 0 busy [0,3); a [0,5) passenger stands to station 3, then takes it for [3,5).
    assert predict_standing_seats([[Leg(0, 3)]], [Leg(0, 5)]) == [SeatOffer(3, 0)]


@pytest.mark.unit
def test_no_seat_when_one_is_occupied_through_the_destination():
    assert predict_standing_seats([[Leg(0, 5)]], [Leg(0, 5)]) == [None]


@pytest.mark.unit
def test_a_coach_with_no_seats_leaves_everyone_standing():
    assert predict_standing_seats([], [Leg(0, 5)]) == [None]


@pytest.mark.unit
def test_earlier_in_queue_claims_the_earlier_freeing_seat():
    # seat 0 frees at 2, seat 1 at 5. Two [0,8) waiters: FIFO gives #0 the earlier seat.
    seats = [[Leg(0, 2)], [Leg(0, 5)]]
    result = predict_standing_seats(seats, [Leg(0, 8), Leg(0, 8)])
    assert result == [SeatOffer(2, 0), SeatOffer(5, 1)]


@pytest.mark.unit
def test_ties_break_to_the_lower_seat_index():
    seats = [[Leg(0, 3)], [Leg(0, 3)]]  # both free at 3
    assert predict_standing_seats(seats, [Leg(0, 5)]) == [SeatOffer(3, 0)]


@pytest.mark.unit
def test_passenger_boarding_midroute_ignores_earlier_occupancy():
    # seat busy [0,2). A [2,5) traveller can sit from 2, since that leg has ended.
    assert predict_standing_seats([[Leg(0, 2)]], [Leg(2, 5)]) == [SeatOffer(2, 0)]


@pytest.mark.unit
@given(seat_sets(), leg_sets())
def test_every_offer_falls_within_the_passengers_leg(seats, queue):
    offers = predict_standing_seats(seats, queue)
    assert len(offers) == len(queue)
    for leg, offer in zip(queue, offers, strict=True):
        if offer is not None:
            assert leg.origin_seq <= offer.board_seq < leg.dest_seq
            assert 0 <= offer.seat_index < len(seats)


@pytest.mark.unit
@given(seat_sets(), leg_sets())
def test_promotions_never_double_seat_a_seat(seats, queue):
    # applying every offer keeps each seat's intervals pairwise non-overlapping.
    # The standing sweep never seats two people on one seat at once.
    offers = predict_standing_seats(seats, queue)
    assigned = [list(seat) for seat in seats]
    for leg, offer in zip(queue, offers, strict=True):
        if offer is not None:
            assigned[offer.seat_index].append(Leg(offer.board_seq, leg.dest_seq))
    for seat_legs in assigned:
        for i in range(len(seat_legs)):
            for j in range(i + 1, len(seat_legs)):
                assert not seat_legs[i].overlaps(seat_legs[j])
