import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import BookingNotFound, IllegalTransition, PaymentDeclined
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat


def _hold(deps):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        passenger_name="Ann Perera",
    )


@pytest.mark.integration
def test_confirm_pays_and_returns_the_receipt():
    deps = build()
    hold = _hold(deps)
    receipt = confirm_booking(deps, booking_id=hold.booking_id)
    assert receipt.status is BookingStatus.CONFIRMED
    assert deps.payment.charges[0][0] == hold.reference
    assert deps.uow.bookings.get(hold.booking_id).status is BookingStatus.CONFIRMED


@pytest.mark.integration
def test_the_receipt_carries_the_ticket_the_passenger_keeps():
    deps = build()
    hold = _hold(deps)
    receipt = confirm_booking(deps, booking_id=hold.booking_id)
    assert receipt.qr_payload == receipt.reference == hold.reference
    assert (receipt.coach, receipt.seat_label) == ("R1", "1A")
    assert (receipt.origin_code, receipt.dest_code) == ("S0", "S3")
    assert (receipt.train_no, receipt.train_name) == ("1005", "Test Express")
    assert receipt.passenger_name == "Ann Perera"
    assert receipt.standing is None


@pytest.mark.integration
def test_the_price_charged_is_the_price_fixed_when_the_seat_was_held():
    """The demand multiplier (D4) keeps moving as the coach fills; the passenger's
    quoted fare does not."""
    deps = build()
    hold = _hold(deps)
    receipt = confirm_booking(deps, booking_id=hold.booking_id)
    assert receipt.fare.cents == hold.fare_cents
    assert deps.payment.charges[0][1].cents == hold.fare_cents


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
