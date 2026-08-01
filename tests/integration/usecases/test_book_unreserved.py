import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import AbuseSuspected
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.book_unreserved import book_unreserved

_LEG = Leg(0, 5)


def _book(deps, passenger="nic-123", leg=_LEG):
    return book_unreserved(
        deps,
        trip_id="trip-1",
        leg=leg,
        passenger_id=passenger,
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_unreserved_booking_is_pending_and_seatless():
    deps = build()
    pending = _book(deps)
    assert pending.status is BookingStatus.PENDING
    assert pending.seat_id == ""
    assert deps.notifier.sent[0][1] == "unreserved_booked"
    assert deps.notifier.sent[0][2]["action"] == "pay_at_counter"


@pytest.mark.integration
def test_pending_booking_holds_no_seat_and_no_availability_event():
    deps = build()
    _book(deps)
    assert deps.uow.bookings.active_holds("trip-1") == []
    assert deps.availability.events == []


@pytest.mark.integration
def test_anti_tout_gate_applies_to_unreserved():
    deps = build(abuse_default=0.95)
    with pytest.raises(AbuseSuspected):
        _book(deps)
