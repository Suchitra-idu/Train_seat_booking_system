"""Repository conformance: the overlap invariant, expiry, cancellation-frees-segment,
waitlist FIFO, and transaction semantics. The same suite runs against the real Postgres
adapter in P3.
"""

import pytest

from slr.adapters.memory_repo import MemoryUnitOfWork
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, insert_trip
from slr.domain.errors import OverlapError
from slr.domain.stations import Leg, Station
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.repository import Hold, Seat, Trip, WaitlistEntry


def make_trip(trip_id="trip-1", route="CMB-BAD", date="2026-08-01"):
    stations = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10))
        for i in range(5)
    )
    seats = (
        Seat("seat-1", "C1", CoachType.RESERVED, TravelClass.SECOND, 1),
        Seat("seat-2", "C1", CoachType.RESERVED, TravelClass.SECOND, 2),
    )
    return Trip(trip_id, route, date, stations, seats)


_DEFAULT_LEG = Leg(0, 2)


def make_hold(
    booking_id,
    *,
    seat_id="seat-1",
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
        travel_class=TravelClass.SECOND,
        status=status,
        held_until=held_until,
        created_at=0,
    )


@pytest.fixture(params=["memory", "postgres"])
def uow(request):
    """The same suite runs against the in-memory fake and the real Postgres adapter."""
    trip = make_trip()
    if request.param == "memory":
        yield MemoryUnitOfWork(trips=[trip])
        return
    factory = request.getfixturevalue("pg_session_factory")
    seed = factory()
    insert_trip(seed, trip)
    seed.close()
    unit = SqlAlchemyUnitOfWork(factory)
    yield unit
    unit.close()


# ── the overlap invariant (D2) ────────────────────────────────────────────────


@pytest.mark.integration
def test_add_hold_round_trips(uow):
    uow.bookings.add_hold(make_hold("b1"))
    assert uow.bookings.get("b1").booking_id == "b1"


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
    assert len(uow.bookings.active_for_seat("trip-1", "seat-1")) == 2


@pytest.mark.integration
def test_same_leg_on_a_different_seat_is_allowed(uow):
    uow.bookings.add_hold(make_hold("b1", seat_id="seat-1", leg=Leg(0, 3)))
    uow.bookings.add_hold(make_hold("b2", seat_id="seat-2", leg=Leg(0, 3)))
    assert len(uow.bookings.active_holds("trip-1")) == 2


@pytest.mark.integration
def test_cancellation_frees_the_segment(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3)))
    uow.bookings.set_status("b1", BookingStatus.CANCELLED)
    # the overlapping leg now books cleanly
    uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2)))
    assert uow.bookings.get("b2").status is BookingStatus.HELD


# ── expiry (D12) ──────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_expire_due_flips_only_overdue_held(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 2), held_until=1_000))
    uow.bookings.add_hold(make_hold("b2", seat_id="seat-2", leg=Leg(0, 2), held_until=2_000))
    expired = uow.bookings.expire_due(now=1_000)
    assert [h.booking_id for h in expired] == ["b1"]
    assert uow.bookings.get("b1").status is BookingStatus.EXPIRED
    assert uow.bookings.get("b2").status is BookingStatus.HELD


@pytest.mark.integration
def test_expiry_frees_the_segment(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 3), held_until=1_000))
    uow.bookings.expire_due(now=1_000)
    uow.bookings.add_hold(make_hold("b2", leg=Leg(1, 2)))
    assert len(uow.bookings.active_for_seat("trip-1", "seat-1")) == 1


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


# ── counter seat assignment (D21) ─────────────────────────────────────────────


@pytest.mark.integration
def test_assign_seat_attaches_a_seat_to_a_pending_booking(uow):
    uow.bookings.add_hold(
        make_hold("b1", seat_id="", status=BookingStatus.PENDING, held_until=9_999)
    )
    assigned = uow.bookings.assign_seat("b1", "seat-1")
    assert assigned.seat_id == "seat-1"
    assert uow.bookings.get("b1").seat_id == "seat-1"


@pytest.mark.integration
def test_by_status_counts_seatless_bookings(uow):
    uow.bookings.add_hold(make_hold("b1", leg=Leg(0, 2)))  # HELD
    uow.bookings.add_hold(
        make_hold("b2", seat_id="", leg=Leg(0, 2), status=BookingStatus.PENDING)
    )
    assert [h.booking_id for h in uow.bookings.by_status("trip-1", BookingStatus.PENDING)] == [
        "b2"
    ]
    assert uow.bookings.by_status("trip-1", BookingStatus.STANDING) == []


# ── trips ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_trip_get_and_find(uow):
    assert uow.trips.get("trip-1").route_code == "CMB-BAD"
    assert len(uow.trips.find("CMB-BAD", "2026-08-01")) == 1
    assert uow.trips.find("CMB-BAD", "2099-01-01") == []


# ── waitlist (D16) ────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_waitlist_next_compatible_is_fifo_among_servable(uow):
    w = uow.waitlist
    w.add(WaitlistEntry("e1", "trip-1", Leg(0, 2), "p1", TravelClass.SECOND, created_at=5))
    w.add(WaitlistEntry("e2", "trip-1", Leg(0, 4), "p2", TravelClass.SECOND, created_at=3))
    w.add(WaitlistEntry("e3", "trip-1", Leg(1, 3), "p3", TravelClass.FIRST, created_at=1))
    # freed [0,4) 2nd class: e1 and e2 both fit; earliest created_at wins.
    assert w.next_compatible("trip-1", Leg(0, 4), TravelClass.SECOND).waitlist_id == "e2"
    # freed [0,2) 2nd class: e2 needs [0,4), so only e1 fits.
    assert w.next_compatible("trip-1", Leg(0, 2), TravelClass.SECOND).waitlist_id == "e1"
    # class must match.
    assert w.next_compatible("trip-1", Leg(0, 4), TravelClass.FIRST).waitlist_id == "e3"
    # nothing servable.
    assert w.next_compatible("trip-1", Leg(0, 1), TravelClass.THIRD) is None


@pytest.mark.integration
def test_waitlist_remove_and_for_trip(uow):
    w = uow.waitlist
    w.add(WaitlistEntry("e1", "trip-1", Leg(0, 2), "p1", TravelClass.SECOND, created_at=1))
    w.add(WaitlistEntry("e2", "trip-2", Leg(0, 2), "p2", TravelClass.SECOND, created_at=1))
    assert {e.waitlist_id for e in w.for_trip("trip-1")} == {"e1"}
    w.remove("e1")
    assert w.for_trip("trip-1") == []


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
