import pytest
from tests.integration.usecases._helpers import build

from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.join_waitlist import join_waitlist
from slr.usecases.promote_waitlist import promote_waitlist


@pytest.mark.integration
def test_promote_places_the_oldest_compatible_waiter():
    deps = build()
    join_waitlist(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 2),
        passenger_id="p1",
        travel_class=TravelClass.SECOND,
    )
    promoted = promote_waitlist(
        deps,
        trip_id="trip-1",
        freed_leg=Leg(0, 3),
        seat_id="R1",
        travel_class=TravelClass.SECOND,
    )
    assert promoted is not None
    assert promoted.passenger_id == "p1"
    assert promoted.status is BookingStatus.HELD


@pytest.mark.integration
def test_promote_returns_none_with_an_empty_waitlist():
    deps = build()
    assert (
        promote_waitlist(
            deps,
            trip_id="trip-1",
            freed_leg=Leg(0, 3),
            seat_id="R1",
            travel_class=TravelClass.SECOND,
        )
        is None
    )
