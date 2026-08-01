"""Repository ports and the records that cross them.

The overlap invariant (D2) is a contract here: add_hold raises OverlapError when a leg
collides with an active hold on the same trip and seat. Records are frozen, so a status
change is a new record and the fake's transaction rollback stays honest.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Protocol

from slr.domain.stations import Leg, Station
from slr.domain.values import BookingStatus, CoachType, TravelClass


@dataclass(frozen=True, slots=True)
class Seat:
    seat_id: str
    coach: str
    coach_type: CoachType
    travel_class: TravelClass
    number: int


@dataclass(frozen=True, slots=True)
class Trip:
    trip_id: str
    route_code: str
    service_date: str
    stations: tuple[Station, ...]
    seats: tuple[Seat, ...]


@dataclass(frozen=True, slots=True)
class Hold:
    """One seat's occupancy over one leg. held_until is the expiry epoch for a HELD
    booking. CONFIRMED holds ignore it."""

    booking_id: str
    reference: str
    trip_id: str
    seat_id: str
    leg: Leg
    passenger_id: str
    travel_class: TravelClass
    status: BookingStatus
    held_until: int
    created_at: int


@dataclass(frozen=True, slots=True)
class WaitlistEntry:
    waitlist_id: str
    trip_id: str
    leg: Leg
    passenger_id: str
    travel_class: TravelClass
    created_at: int


class TripRepository(Protocol):
    def get(self, trip_id: str) -> Trip:
        """Raises KeyError if no such trip."""
        ...

    def find(self, route_code: str, service_date: str) -> list[Trip]:
        ...


class BookingRepository(Protocol):
    def add_hold(self, hold: Hold) -> None:
        """Persist a hold. Raises OverlapError on overlap with an active hold (D2)."""
        ...

    def get(self, booking_id: str) -> Hold:
        """Raises KeyError if no such booking."""
        ...

    def by_reference(self, reference: str) -> Hold | None:
        """Idempotency lookup. None if the reference was never held."""
        ...

    def set_status(self, booking_id: str, status: BookingStatus) -> Hold:
        """Transition an existing booking; returns the updated record."""
        ...

    def assign_seat(self, booking_id: str, seat_id: str) -> Hold:
        """Attach a seat to a seatless booking at counter settlement (D21). Returns the
        updated record. Raises OverlapError if the seat is already actively held over the
        booking's leg."""
        ...

    def active_for_seat(self, trip_id: str, seat_id: str) -> list[Hold]:
        ...

    def active_for_passenger(self, trip_id: str, passenger_id: str) -> list[Hold]:
        ...

    def active_holds(self, trip_id: str) -> list[Hold]:
        """Every HELD/CONFIRMED hold on the trip. The occupancy for availability."""
        ...

    def by_status(self, trip_id: str, status: BookingStatus) -> list[Hold]:
        """Every booking on the trip in one status. Counts PENDING/STANDING outside the
        active-occupancy queries."""
        ...

    def expire_due(self, now: int) -> list[Hold]:
        """Flip every HELD whose `held_until <= now` to EXPIRED; return them (D12)."""
        ...


class WaitlistRepository(Protocol):
    def add(self, entry: WaitlistEntry) -> None:
        ...

    def next_compatible(
        self, trip_id: str, leg: Leg, travel_class: TravelClass
    ) -> WaitlistEntry | None:
        """FIFO among entries whose leg/class the freed segment can serve (D16)."""
        ...

    def remove(self, waitlist_id: str) -> None:
        ...

    def for_trip(self, trip_id: str) -> list[WaitlistEntry]:
        ...


class UnitOfWork(Protocol):
    bookings: BookingRepository
    trips: TripRepository
    waitlist: WaitlistRepository

    def __enter__(self) -> UnitOfWork:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
