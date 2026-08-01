"""In-memory repositories and UnitOfWork. The infra-free stand-in for Postgres.

add_hold replicates the overlap invariant (D2): a leg may not overlap an active
(HELD/CONFIRMED) hold on the same trip and seat. The UoW snapshots on enter and restores
on rollback, so uncommitted work behaves like a real transaction.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from types import TracebackType

from slr.domain.errors import OverlapError
from slr.domain.stations import Leg
from slr.domain.values import ACTIVE_STATUSES, BookingStatus, TravelClass
from slr.ports.repository import (
    BookingRepository,
    Hold,
    Trip,
    TripRepository,
    WaitlistEntry,
    WaitlistRepository,
)


class _Store:
    def __init__(self) -> None:
        self.holds: dict[str, Hold] = {}
        self.trips: dict[str, Trip] = {}
        self.waitlist: dict[str, WaitlistEntry] = {}


class MemoryTripRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def get(self, trip_id: str) -> Trip:
        return self._store.trips[trip_id]

    def find(self, route_code: str, service_date: str) -> list[Trip]:
        return [
            t
            for t in self._store.trips.values()
            if t.route_code == route_code and t.service_date == service_date
        ]


class MemoryBookingRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def add_hold(self, hold: Hold) -> None:
        for existing in self.active_for_seat(hold.trip_id, hold.seat_id):
            if existing.booking_id == hold.booking_id:
                continue
            if existing.leg.overlaps(hold.leg):
                raise OverlapError(
                    f"seat {hold.seat_id} already held over {existing.leg} "
                    f"on trip {hold.trip_id}"
                )
        self._store.holds[hold.booking_id] = hold

    def get(self, booking_id: str) -> Hold:
        return self._store.holds[booking_id]

    def by_reference(self, reference: str) -> Hold | None:
        for hold in self._store.holds.values():
            if hold.reference == reference:
                return hold
        return None

    def set_status(self, booking_id: str, status: BookingStatus) -> Hold:
        updated = replace(self._store.holds[booking_id], status=status)
        self._store.holds[booking_id] = updated
        return updated

    def assign_seat(self, booking_id: str, seat_id: str) -> Hold:
        hold = self._store.holds[booking_id]
        for existing in self.active_for_seat(hold.trip_id, seat_id):
            if existing.booking_id == booking_id:
                continue
            if existing.leg.overlaps(hold.leg):
                raise OverlapError(
                    f"seat {seat_id} already held over {existing.leg} "
                    f"on trip {hold.trip_id}"
                )
        updated = replace(hold, seat_id=seat_id)
        self._store.holds[booking_id] = updated
        return updated

    def active_for_seat(self, trip_id: str, seat_id: str) -> list[Hold]:
        return [
            h
            for h in self._store.holds.values()
            if h.trip_id == trip_id
            and h.seat_id == seat_id
            and h.status in ACTIVE_STATUSES
        ]

    def active_for_passenger(self, trip_id: str, passenger_id: str) -> list[Hold]:
        return [
            h
            for h in self._store.holds.values()
            if h.trip_id == trip_id
            and h.passenger_id == passenger_id
            and h.status in ACTIVE_STATUSES
        ]

    def active_holds(self, trip_id: str) -> list[Hold]:
        return [
            h
            for h in self._store.holds.values()
            if h.trip_id == trip_id and h.status in ACTIVE_STATUSES
        ]

    def by_status(self, trip_id: str, status: BookingStatus) -> list[Hold]:
        return [
            h
            for h in self._store.holds.values()
            if h.trip_id == trip_id and h.status is status
        ]

    def expire_due(self, now: int) -> list[Hold]:
        expired: list[Hold] = []
        for booking_id, hold in list(self._store.holds.items()):
            if hold.status is BookingStatus.HELD and hold.held_until <= now:
                updated = replace(hold, status=BookingStatus.EXPIRED)
                self._store.holds[booking_id] = updated
                expired.append(updated)
        return expired


class MemoryWaitlistRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def add(self, entry: WaitlistEntry) -> None:
        self._store.waitlist[entry.waitlist_id] = entry

    def next_compatible(
        self, trip_id: str, leg: Leg, travel_class: TravelClass
    ) -> WaitlistEntry | None:
        # FIFO among entries the freed segment can serve: the freed leg must cover the
        # waiter's leg (waiter's interval within the freed interval).
        servable = [
            e
            for e in self._store.waitlist.values()
            if e.trip_id == trip_id
            and e.travel_class == travel_class
            and leg.origin_seq <= e.leg.origin_seq
            and e.leg.dest_seq <= leg.dest_seq
        ]
        if not servable:
            return None
        return min(servable, key=lambda e: (e.created_at, e.waitlist_id))

    def remove(self, waitlist_id: str) -> None:
        self._store.waitlist.pop(waitlist_id, None)

    def for_trip(self, trip_id: str) -> list[WaitlistEntry]:
        return [e for e in self._store.waitlist.values() if e.trip_id == trip_id]


class MemoryUnitOfWork:
    def __init__(
        self, store: _Store | None = None, *, trips: Iterable[Trip] = ()
    ) -> None:
        self._store = store or _Store()
        for trip in trips:
            self._store.trips[trip.trip_id] = trip
        self.bookings: BookingRepository = MemoryBookingRepository(self._store)
        self.trips: TripRepository = MemoryTripRepository(self._store)
        self.waitlist: WaitlistRepository = MemoryWaitlistRepository(self._store)
        self._snapshot: (
            tuple[dict[str, Hold], dict[str, Trip], dict[str, WaitlistEntry]] | None
        ) = None

    def __enter__(self) -> MemoryUnitOfWork:
        self._snapshot = (
            dict(self._store.holds),
            dict(self._store.trips),
            dict(self._store.waitlist),
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Commit clears the snapshot and persists. Any other exit restores the pre-block
        # state, like a rolled-back transaction.
        if self._snapshot is not None:
            self.rollback()

    def commit(self) -> None:
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            holds, trips, waitlist = self._snapshot
            self._store.holds = holds
            self._store.trips = trips
            self._store.waitlist = waitlist
            self._snapshot = None
