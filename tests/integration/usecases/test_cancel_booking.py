import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import BookingNotFound, IllegalTransition, OverlapError
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.usecases.cancel_booking import cancel_booking
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat

_LEG = Leg(0, 3)


def _hold(deps, seat_id="R1", leg=_LEG, passenger="p1"):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        passenger_name="Ann Perera",
    )


@pytest.mark.integration
def test_cancel_frees_the_segment_for_the_next_booker():
    """No waiting queue to promote into (D16 withdrawn): the leg simply reopens, and the
    SSE delta is how every watching client finds out."""
    deps = build()
    hold = _hold(deps, passenger="p1")
    with pytest.raises(OverlapError):
        _hold(deps, leg=Leg(1, 2), passenger="p2")

    cancelled = cancel_booking(deps, booking_id=hold.booking_id)
    assert cancelled.status is BookingStatus.CANCELLED
    assert deps.availability.events[-1].status is BookingStatus.CANCELLED

    reopened = _hold(deps, leg=Leg(1, 2), passenger="p2")
    assert reopened.status is BookingStatus.HELD


@pytest.mark.integration
def test_a_confirmed_booking_can_be_cancelled():
    deps = build()
    hold = _hold(deps)
    confirm_booking(deps, booking_id=hold.booking_id)
    assert cancel_booking(deps, booking_id=hold.booking_id).status is BookingStatus.CANCELLED


@pytest.mark.integration
def test_double_cancel_is_illegal():
    deps = build()
    hold = _hold(deps)
    cancel_booking(deps, booking_id=hold.booking_id)
    with pytest.raises(IllegalTransition):
        cancel_booking(deps, booking_id=hold.booking_id)


@pytest.mark.integration
def test_cancelling_an_unknown_booking_is_not_found():
    deps = build()
    with pytest.raises(BookingNotFound):
        cancel_booking(deps, booking_id="nope")
