import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, build, make_trip

from slr.domain.errors import (
    AbuseSuspected,
    CoachFull,
    InvalidLeg,
    PaymentDeclined,
    SeatNotBookable,
)
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.usecases.sell_unreserved import sell_unreserved


def _sell(deps, passenger="nic-1", leg=None, name="Ann Perera", **kw):
    leg = leg if leg is not None else Leg(0, 5)
    return sell_unreserved(
        deps,
        trip_id="trip-1",
        leg=leg,
        passenger_id=passenger,
        passenger_name=name,
        travel_class=TravelClass.SECOND,
        **kw,
    )


@pytest.mark.integration
def test_a_sale_is_paid_seated_and_final_in_one_step():
    """D23: the counter creates and settles in one transaction, so there is no unpaid
    booking sitting on capacity."""
    deps = build()
    receipt = _sell(deps)
    assert receipt.status is BookingStatus.CONFIRMED
    assert receipt.seat_label is not None
    assert receipt.coach == "U1"
    assert receipt.passenger_name == "Ann Perera"
    assert deps.payment.charges[0][0] == receipt.reference

    booking = deps.uow.bookings.by_reference(receipt.reference)
    assert booking.status is BookingStatus.CONFIRMED
    assert booking.fare_cents == receipt.fare.cents


@pytest.mark.integration
def test_the_receipt_carries_the_qr_payload_and_the_journey():
    deps = build()
    receipt = _sell(deps, leg=Leg(0, 3))
    assert receipt.qr_payload == receipt.reference
    assert (receipt.origin_code, receipt.dest_code) == ("S0", "S3")
    assert receipt.train_no == "1005"
    assert receipt.depart == "08:05"


@pytest.mark.integration
def test_seats_are_packed_so_a_second_sale_reuses_a_free_seat():
    deps = build(trip=make_trip(unreserved=2))
    first = _sell(deps, "nic-1", Leg(0, 2))
    second = _sell(deps, "nic-2", Leg(2, 5))  # adjacent, so the same seat serves both
    assert first.seat_label == second.seat_label


@pytest.mark.integration
def test_standing_is_issued_with_the_station_a_seat_frees_at():
    deps = build(trip=make_trip(unreserved=1))
    _sell(deps, "nic-1", Leg(0, 3))  # takes the only seat over [0,3)
    receipt = _sell(deps, "nic-2", Leg(0, 5))

    assert receipt.status is BookingStatus.STANDING
    assert receipt.seat_label is None
    assert receipt.standing is not None
    assert receipt.standing.after_seq == 3
    assert receipt.standing.after_station == "Station 3"
    assert receipt.standing.seat_label == "1A"


@pytest.mark.integration
def test_standing_capacity_is_the_hard_ceiling():
    deps = build(
        trip=make_trip(unreserved=1),
        config={**DEFAULT_CONFIG, "standing_capacity_per_coach": 1},
    )
    _sell(deps, "nic-1", Leg(0, 5))  # seated
    _sell(deps, "nic-2", Leg(0, 5))  # standing
    with pytest.raises(CoachFull):
        _sell(deps, "nic-3", Leg(0, 5))


@pytest.mark.integration
def test_a_declined_charge_leaves_no_booking_behind():
    deps = build(decline=True)
    with pytest.raises(PaymentDeclined):
        _sell(deps)
    assert deps.uow.bookings.active_holds("trip-1") == []
    assert deps.uow.bookings.by_reference("SLR-000001") is None


@pytest.mark.integration
def test_a_train_with_no_unreserved_coach_of_that_class_cannot_sell():
    deps = build(trip=make_trip(unreserved=0))
    with pytest.raises(SeatNotBookable):
        _sell(deps)


@pytest.mark.integration
def test_a_leg_off_the_route_fails_loud():
    deps = build()
    with pytest.raises(InvalidLeg):
        _sell(deps, leg=Leg(0, 99))


@pytest.mark.integration
def test_the_anti_tout_gate_applies_at_the_counter_too():
    deps = build(abuse_default=0.95)
    with pytest.raises(AbuseSuspected):
        _sell(deps)


@pytest.mark.integration
def test_a_replayed_reference_returns_the_same_ticket_without_charging_twice():
    deps = build()
    first = _sell(deps, reference="SLR-COUNTER-1")
    again = _sell(deps, reference="SLR-COUNTER-1")
    assert again.reference == first.reference
    assert again.seat_label == first.seat_label
    assert len(deps.payment.charges) == 1


@pytest.mark.integration
def test_a_standing_ticket_holds_no_seat_and_publishes_no_availability_delta():
    deps = build(trip=make_trip(unreserved=1))
    deps.availability.events.clear()
    _sell(deps, "nic-1", Leg(0, 3))
    seated_events = len(deps.availability.events)

    _sell(deps, "nic-2", Leg(0, 5))  # standing
    assert len(deps.availability.events) == seated_events
