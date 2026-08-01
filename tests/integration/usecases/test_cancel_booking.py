import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import IllegalTransition
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.book_unreserved import book_unreserved
from slr.usecases.cancel_booking import cancel_booking
from slr.usecases.hold_seat import hold_seat
from slr.usecases.join_waitlist import join_waitlist

_LEG = Leg(0, 3)


def _hold(deps, seat_id="R1", leg=_LEG, passenger="p1"):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_cancel_frees_the_seat_and_promotes_the_waitlist():
    deps = build()
    hold = _hold(deps, passenger="p1")
    join_waitlist(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 3),
        passenger_id="p2",
        travel_class=TravelClass.SECOND,
    )
    result = cancel_booking(deps, booking_id=hold.booking_id)
    assert result.cancelled.status is BookingStatus.CANCELLED
    assert result.promoted is not None
    assert result.promoted.passenger_id == "p2"
    assert result.promoted.seat_id == "R1"
    assert deps.uow.waitlist.for_trip("trip-1") == []


@pytest.mark.integration
def test_double_cancel_is_illegal():
    deps = build()
    hold = _hold(deps)
    cancel_booking(deps, booking_id=hold.booking_id)
    with pytest.raises(IllegalTransition):
        cancel_booking(deps, booking_id=hold.booking_id)


@pytest.mark.integration
def test_cancelling_a_pending_booking_promotes_nothing():
    deps = build()
    pending = book_unreserved(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 5),
        passenger_id="nic-1",
        travel_class=TravelClass.SECOND,
    )
    result = cancel_booking(deps, booking_id=pending.booking_id)
    assert result.promoted is None
    assert result.cancelled.status is BookingStatus.CANCELLED
