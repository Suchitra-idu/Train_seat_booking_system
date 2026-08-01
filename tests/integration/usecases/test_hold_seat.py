import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, build

from slr.domain.errors import (
    AbuseSuspected,
    OverlapError,
    SeatCapExceeded,
    SeatNotBookable,
    VelocityExceeded,
)
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.usecases.hold_seat import hold_seat

_LEG = Leg(0, 3)


def _hold(deps, seat_id="R1", leg=_LEG, passenger="p1", reference=None):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        passenger_name="Ann Perera",
        reference=reference,
    )


@pytest.mark.integration
def test_hold_creates_a_held_booking_and_notifies():
    deps = build()
    hold = _hold(deps)
    assert hold.status is BookingStatus.HELD
    assert hold.held_until == 1_000 + DEFAULT_CONFIG["hold_ttl_seconds"]
    assert deps.notifier.sent[0][1] == "seat_held"
    assert deps.availability.events[0].status is BookingStatus.HELD


@pytest.mark.integration
def test_overlapping_hold_on_the_same_seat_is_rejected():
    deps = build()
    _hold(deps, leg=Leg(0, 3), passenger="p1")
    with pytest.raises(OverlapError):
        _hold(deps, leg=Leg(1, 2), passenger="p2")


@pytest.mark.integration
def test_non_reserved_seat_cannot_be_picked():
    deps = build()
    with pytest.raises(SeatNotBookable):
        _hold(deps, seat_id="U1")


@pytest.mark.integration
def test_idempotent_replay_returns_the_same_booking():
    deps = build()
    first = _hold(deps, reference="SLR-fixed")
    again = _hold(deps, reference="SLR-fixed")
    assert again.booking_id == first.booking_id
    assert len(deps.uow.bookings.active_holds("trip-1")) == 1


@pytest.mark.integration
def test_seat_cap_blocks_a_further_hold():
    deps = build(config={**DEFAULT_CONFIG, "max_seats_per_passenger": 1})
    _hold(deps, seat_id="R1", leg=Leg(0, 2))
    with pytest.raises(SeatCapExceeded):
        _hold(deps, seat_id="R2", leg=Leg(0, 2))


@pytest.mark.integration
def test_velocity_limit_blocks_a_burst():
    deps = build(config={**DEFAULT_CONFIG, "max_bookings_per_window": 1})
    _hold(deps, seat_id="R1", leg=Leg(0, 2))
    with pytest.raises(VelocityExceeded):
        _hold(deps, seat_id="R2", leg=Leg(0, 2))


@pytest.mark.integration
def test_high_abuse_score_blocks_the_hold():
    deps = build(abuse_default=0.95)
    with pytest.raises(AbuseSuspected):
        _hold(deps)
