import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, build, make_trip

from slr.domain.errors import BookingNotFound
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.cancel_booking import cancel_booking
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat
from slr.usecases.sell_unreserved import sell_unreserved
from slr.usecases.verify_ticket import Verdict, verify_ticket


def _hold(deps, seat_id="R1", leg=None, passenger="nic-1"):
    leg = leg if leg is not None else Leg(0, 3)
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        passenger_name="Ann Perera",
    )


@pytest.mark.integration
def test_a_paid_reserved_ticket_is_valid():
    deps = build()
    booking = _hold(deps)
    confirm_booking(deps, booking_id=booking.booking_id)

    result = verify_ticket(deps, reference=booking.reference)
    assert result.verdict is Verdict.VALID
    assert result.valid
    assert result.receipt.passenger_id == "nic-1"
    assert result.receipt.passenger_name == "Ann Perera"
    assert result.receipt.seat_label == "1A"


@pytest.mark.integration
def test_a_counter_sale_verifies_the_same_way_as_an_app_booking():
    """One receipt shape for both channels (D24), so the inspector reads one screen."""
    deps = build()
    receipt = sell_unreserved(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 5),
        passenger_id="nic-9",
        passenger_name="Nimal Silva",
        travel_class=TravelClass.SECOND,
    )
    result = verify_ticket(deps, reference=receipt.reference)
    assert result.verdict is Verdict.VALID
    assert result.receipt.passenger_id == "nic-9"


@pytest.mark.integration
def test_a_standing_ticket_is_valid_and_carries_no_seat():
    deps = build(trip=make_trip(unreserved=1))
    sell_unreserved(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 3),
        passenger_id="nic-1",
        passenger_name="Ann",
        travel_class=TravelClass.SECOND,
    )
    standing = sell_unreserved(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 5),
        passenger_id="nic-2",
        passenger_name="Bee",
        travel_class=TravelClass.SECOND,
    )
    result = verify_ticket(deps, reference=standing.reference)
    assert result.verdict is Verdict.VALID
    assert result.receipt.seat_label is None


@pytest.mark.integration
def test_an_unpaid_hold_is_not_a_valid_ticket():
    deps = build()
    booking = _hold(deps)
    result = verify_ticket(deps, reference=booking.reference)
    assert result.verdict is Verdict.UNPAID
    assert not result.valid


@pytest.mark.integration
def test_a_cancelled_ticket_says_so():
    deps = build()
    booking = _hold(deps)
    confirm_booking(deps, booking_id=booking.booking_id)
    cancel_booking(deps, booking_id=booking.booking_id)
    assert verify_ticket(deps, reference=booking.reference).verdict is Verdict.CANCELLED


@pytest.mark.integration
def test_an_expired_hold_says_so():
    deps = build(config={**DEFAULT_CONFIG, "hold_ttl_seconds": 1})
    booking = _hold(deps)
    deps.clock.advance(5)
    assert verify_ticket(deps, reference=booking.reference).verdict is Verdict.EXPIRED


@pytest.mark.integration
def test_a_forged_or_mistyped_reference_is_not_found():
    """The whole trust model of the QR (D24): the server either has it or it does not."""
    deps = build()
    with pytest.raises(BookingNotFound):
        verify_ticket(deps, reference="SLR-FORGED")


@pytest.mark.integration
def test_verification_never_mutates_the_booking():
    deps = build()
    booking = _hold(deps)
    confirm_booking(deps, booking_id=booking.booking_id)
    before = deps.uow.bookings.get(booking.booking_id)
    verify_ticket(deps, reference=booking.reference)
    assert deps.uow.bookings.get(booking.booking_id) == before
