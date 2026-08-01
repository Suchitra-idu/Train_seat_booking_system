import pytest
from tests.integration.usecases._helpers import build

from slr.domain.stations import Leg
from slr.usecases.hold_seat import hold_seat
from slr.usecases.leg_availability import leg_availability


@pytest.mark.integration
def test_all_seats_free_on_a_fresh_trip():
    deps = build()
    view = leg_availability(deps, trip_id="trip-1", leg=Leg(0, 2))
    assert view.free_count == len(view.seats)
    assert all(s.available for s in view.seats)


@pytest.mark.integration
def test_a_held_seat_is_unavailable_only_over_the_overlapping_leg():
    deps = build()
    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        passenger_name="Ann Perera",
    )
    over = {
        s.seat_id: s.available
        for s in leg_availability(deps, trip_id="trip-1", leg=Leg(1, 2)).seats
    }
    after = {
        s.seat_id: s.available
        for s in leg_availability(deps, trip_id="trip-1", leg=Leg(3, 5)).seats
    }
    assert over["R1"] is False
    assert after["R1"] is True  # adjacent segment is free, that is segment resale


@pytest.mark.integration
def test_expired_hold_frees_the_seat():
    deps = build()
    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        passenger_name="Ann Perera",
    )
    deps.clock.advance(10_000)  # past the hold TTL
    view = leg_availability(deps, trip_id="trip-1", leg=Leg(0, 3))
    assert {s.seat_id: s.available for s in view.seats}["R1"] is True
