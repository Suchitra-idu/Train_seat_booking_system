import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, build, make_trip

from slr.domain.errors import (
    BookingNotFound,
    CoachFull,
    IllegalTransition,
    PaymentDeclined,
)
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.book_unreserved import book_unreserved
from slr.usecases.settle_at_counter import settle_at_counter


def _book(deps, passenger, leg):
    return book_unreserved(
        deps,
        trip_id="trip-1",
        leg=leg,
        passenger_id=passenger,
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_settle_assigns_a_seat_and_confirms():
    deps = build()
    pending = _book(deps, "nic-1", Leg(0, 5))
    invoice = settle_at_counter(deps, reference=pending.reference)
    assert invoice.status is BookingStatus.CONFIRMED
    assert invoice.seat_id is not None
    assert invoice.passenger_id == "nic-1"
    assert deps.payment.charges[0][0] == pending.reference
    assert deps.uow.bookings.get(pending.booking_id).seat_id == invoice.seat_id


@pytest.mark.integration
def test_settle_predicts_a_seat_that_frees_mid_leg():
    deps = build(trip=make_trip(unreserved=1))
    first = _book(deps, "nic-1", Leg(0, 3))
    settle_at_counter(deps, reference=first.reference)  # takes U1 over [0,3)
    second = _book(deps, "nic-2", Leg(0, 5))
    invoice = settle_at_counter(deps, reference=second.reference)
    assert invoice.status is BookingStatus.STANDING
    assert invoice.seat_id is None
    assert invoice.standing_after == 3  # sit on the seat after station 3
    assert invoice.standing_seat == 1


@pytest.mark.integration
def test_standing_capacity_is_the_hard_ceiling():
    deps = build(
        trip=make_trip(unreserved=1),
        config={**DEFAULT_CONFIG, "standing_capacity_per_coach": 1},
    )
    settle_at_counter(deps, reference=_book(deps, "nic-1", Leg(0, 5)).reference)  # seat
    settle_at_counter(deps, reference=_book(deps, "nic-2", Leg(0, 5)).reference)  # standing
    with pytest.raises(CoachFull):
        settle_at_counter(deps, reference=_book(deps, "nic-3", Leg(0, 5)).reference)


@pytest.mark.integration
def test_declined_charge_leaves_the_booking_pending():
    deps = build(decline=True)
    pending = _book(deps, "nic-1", Leg(0, 5))
    with pytest.raises(PaymentDeclined):
        settle_at_counter(deps, reference=pending.reference)
    assert deps.uow.bookings.get(pending.booking_id).status is BookingStatus.PENDING


@pytest.mark.integration
def test_unknown_reference_is_not_found():
    deps = build()
    with pytest.raises(BookingNotFound):
        settle_at_counter(deps, reference="SLR-nope")


@pytest.mark.integration
def test_double_settle_is_rejected():
    deps = build()
    pending = _book(deps, "nic-1", Leg(0, 5))
    settle_at_counter(deps, reference=pending.reference)
    with pytest.raises(IllegalTransition):
        settle_at_counter(deps, reference=pending.reference)
