import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import BookingNotFound, IllegalTransition, PaymentDeclined
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat


def _hold(deps):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_confirm_pays_and_transitions_to_confirmed():
    deps = build()
    hold = _hold(deps)
    confirmed = confirm_booking(deps, booking_id=hold.booking_id)
    assert confirmed.status is BookingStatus.CONFIRMED
    assert deps.payment.charges[0][0] == hold.reference


@pytest.mark.integration
def test_declined_payment_leaves_the_hold_held():
    deps = build(decline=True)
    hold = _hold(deps)
    with pytest.raises(PaymentDeclined):
        confirm_booking(deps, booking_id=hold.booking_id)
    assert deps.uow.bookings.get(hold.booking_id).status is BookingStatus.HELD


@pytest.mark.integration
def test_expired_hold_cannot_be_confirmed():
    deps = build()
    hold = _hold(deps)
    deps.clock.advance(10_000)  # past the TTL
    with pytest.raises(IllegalTransition):
        confirm_booking(deps, booking_id=hold.booking_id)
    assert deps.payment.charges == []  # no charge on an illegal transition


@pytest.mark.integration
def test_confirm_missing_booking_is_not_found():
    deps = build()
    with pytest.raises(BookingNotFound):
        confirm_booking(deps, booking_id="nope")
