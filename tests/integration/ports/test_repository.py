"""Repository conformance: the overlap invariant, expiry, cancellation-frees-segment,
trip lookup, and transaction semantics. The same suite runs against the in-memory fake and
the real Postgres adapter, which is what makes the fake a trustworthy stand-in.
"""

import pytest
from tests.integration.usecases._helpers import make_trip

from slr.adapters.memory_repo import MemoryUnitOfWork
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, upsert_trip
from slr.domain.errors import OverlapError
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.ports.repository import Hold

_DEFAULT_LEG = Leg(0, 2)


def make_hold(
    booking_id,
    *,
    seat_id="R1",
    leg=_DEFAULT_LEG,
    status=BookingStatus.HELD,
    held_until=1_000,
    passenger="p1",
    reference=None,
    trip_id="trip-1",
):
    return Hold(
        booking_id=booking_id,
        reference=reference or f"ref-{booking_id}",
        trip_id=trip_id,
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        passenger_name=f"Passenger {passenger}",
        travel_class=TravelClass.SECOND,
        status=status,
        fare_cents=10_000,
        held_until=held_until,
        created_at=0,
    )


@pytest.fixture(params=["memory", "postgres"])
def uow(request):
    """The same suite runs against the in-memory fake and the real Postgres adapter."""
    trips = [
        make_trip("trip-1", reserved=2, unreserved=0, service_date="2026-08-01"),
        make_trip("trip-2", reserved=2, unreserved=0, service_date="2026-08-02"),
    ]
    if request.param == "memory":
        yield MemoryUnitOfWork(trips=trips)
        return
    factory = request.getfixturevalue("pg_session_factory")
    seed = factory()
    for trip in trips:
        upsert_trip(seed, trip)
    seed.commit()
    seed.close()
    unit = SqlAlchemyUnitOfWork(factory)
    yield unit
    unit.close()


# ── the overlap invariant (D2) ────────────────────────────────────────────────


@pytest.mark.integration
def test_add_hold_round_trips(uow):
    uow.bookings.add_hold(make_hold("b1"))
    stored = uow.bookings.get("b1")
    assert stored.booking_id == "b1"
    assert stored.passenger_name == "Passenger p1"
    assert stored.fare_cents == 10_000


@pytest.mark.integration
def test_overlapping_active_hold_on_same_seat_is_rejected(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3)))
    with pytest.raises(OverlapError):
        uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2)))


@pytest.mark.integration
def test_adjacent_legs_on_one_seat_both_book(uow):
    # [0,2) then [2,4): the segment-resale journey. No overlap, both hold.
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 2)))
    uow.bookings.add_hold(make_hold("b2", leg=Leg(2, 4)))
    assert len(uow.bookings.active_for_seat("trip-1", "R1")) == 2


@pytest.mark.integration
def test_same_leg_on_a_different_seat_is_allowed(uow):
    uow.bookings.add_hold(make_hold("b1", seat_id="R1", leg=Leg(0, 3)))
    uow.bookings.add_hold(make_hold("b2", seat_id="R2", leg=Leg(0, 3)))
    assert len(uow.bookings.active_holds("trip-1")) == 2


@pytest.mark.integration
def test_the_same_seat_on_another_trip_is_a_different_seat(uow):
    uow.bookings.add_hold(make_hold("b1", trip_id="trip-1", leg=Leg(0, 3)))
    uow.bookings.add_hold(make_hold("b2", trip_id="trip-2", leg=Leg(0, 3)))
    assert len(uow.bookings.active_holds("trip-2")) == 1


@pytest.mark.integration
def test_cancellation_frees_the_segment(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3)))
    uow.bookings.set_status("b1", BookingStatus.CANCELLED)
    # the overlapping leg now books cleanly
    uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2)))
    assert uow.bookings.get("b2").status is BookingStatus.HELD


@pytest.mark.integration
def test_a_standing_ticket_holds_no_seat_and_never_blocks_one(uow):
    """STANDING is live but seatless (D20), so it sits outside the overlap invariant."""
    uow.bookings.add_hold(
        make_hold("b1", seat_id="", leg=Leg(0, 5), status=BookingStatus.STANDING)
    )
    uow.bookings.add_hold(
        make_hold("b2", seat_id="", leg=Leg(0, 5), status=BookingStatus.STANDING)
    )
    assert uow.bookings.active_holds("trip-1") == []
    assert len(uow.bookings.by_status("trip-1", BookingStatus.STANDING)) == 2


# ── expiry (D12) ──────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_expire_due_flips_only_overdue_held(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 2), held_until=1_000))
    uow.bookings.add_hold(make_hold("b2", seat_id="R2", leg=Leg(0, 2), held_until=2_000))
    expired = uow.bookings.expire_due(now=1_000)
    assert [h.booking_id for h in expired] == ["b1"]
    assert uow.bookings.get("b1").status is BookingStatus.EXPIRED
    assert uow.bookings.get("b2").status is BookingStatus.HELD


@pytest.mark.integration
def test_expiry_frees_the_segment(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3), held_until=1_000))
    uow.bookings.expire_due(now=1_000)
    uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2)))
    assert len(uow.bookings.active_for_seat("trip-1", "R1")) == 1


@pytest.mark.integration
def test_confirmed_holds_never_expire(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3), held_until=1))
    uow.bookings.set_status("b1", BookingStatus.CONFIRMED)
    assert uow.bookings.expire_due(now=10_000) == []
    assert uow.bookings.get("b1").status is BookingStatus.CONFIRMED


# ── lookups ───────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_by_reference_is_the_idempotency_key(uow):
    uow.bookings.add_hold(make_hold("b1", reference="SLR-000001"))
    assert uow.bookings.by_reference("SLR-000001").booking_id == "b1"
    assert uow.bookings.by_reference("SLR-999999") is None


@pytest.mark.integration
def test_active_for_passenger_excludes_terminal(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 1), passenger="alice"))
    uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2), passenger="alice"))
    uow.bookings.set_status("b2", BookingStatus.CANCELLED)
    active = uow.bookings.active_for_passenger("trip-1", "alice")
    assert [h.booking_id for h in active] == ["b1"]


@pytest.mark.integration
def test_get_missing_booking_raises_keyerror(uow):
    with pytest.raises(KeyError):
        uow.bookings.get("nope")


# ── trips (D22) ───────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_trip_get_reads_back_the_whole_materialized_trip(uow):
    trip = uow.trips.get("trip-1")
    assert trip.route_code == "CMB-BAD"
    assert trip.train_no == "1005"
    assert [c.code for c in trip.coaches] == ["R1"]
    assert trip.coaches[0].columns == "1-0"
    assert trip.stops[0].depart_min == 485
    assert trip.seats[0].row == 1
    assert trip.seats[0].column == "A"


@pytest.mark.integration
def test_get_missing_trip_raises_keyerror(uow):
    with pytest.raises(KeyError):
        uow.trips.get("no-such-trip")


@pytest.mark.integration
def test_find_by_date_returns_only_that_day(uow):
    assert [t.trip_id for t in uow.trips.find_by_date("2026-08-01")] == ["trip-1"]
    assert [t.trip_id for t in uow.trips.find_by_date("2026-08-02")] == ["trip-2"]
    assert uow.trips.find_by_date("2099-01-01") == []


# ── transaction semantics ─────────────────────────────────────────────────────


@pytest.mark.integration
def test_rollback_discards_uncommitted_writes(uow):
    with uow:
        uow.bookings.add_hold(make_hold("b1"))
    assert uow.bookings.by_reference("ref-b1") is None


@pytest.mark.integration
def test_commit_persists_writes(uow):
    with uow:
        uow.bookings.add_hold(make_hold("b1"))
        uow.commit()
    assert uow.bookings.get("b1").booking_id == "b1"


@pytest.mark.integration
def test_exception_before_commit_rolls_back(uow):
    with pytest.raises(RuntimeError), uow:
        uow.bookings.add_hold(make_hold("b1"))
        raise RuntimeError("boom before commit")
    assert uow.bookings.by_reference("ref-b1") is None
