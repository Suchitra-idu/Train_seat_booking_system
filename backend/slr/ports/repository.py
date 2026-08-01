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
from slr.domain.timetable import Stop
from slr.domain.values import BookingStatus, CoachType, TravelClass


@dataclass(frozen=True, slots=True)
class Coach:
    """A coach's identity and seating geometry (D25). `columns` is the seats-per-side
    pattern ("3-3"); `exit_rows` are rows the map draws a break after."""

    code: str
    coach_type: CoachType
    travel_class: TravelClass
    rows: int
    columns: str
    exit_rows: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Seat:
    seat_id: str
    coach: str
    coach_type: CoachType
    travel_class: TravelClass
    number: int
    row: int
    column: str


@dataclass(frozen=True, slots=True)
class Trip:
    """One dated run of a service pattern (D22). Stations are the line's order; stops are
    this train's calls on it, so a trip that skips a station simply has no stop for it."""

    trip_id: str
    route_code: str
    service_date: str
    train_no: str
    train_name: str
    stations: tuple[Station, ...]
    stops: tuple[Stop, ...]
    coaches: tuple[Coach, ...]
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
    passenger_name: str
    travel_class: TravelClass
    status: BookingStatus
    fare_cents: int
    held_until: int
    created_at: int


class TripRepository(Protocol):
    def get(self, trip_id: str) -> Trip:
        """Raises KeyError if no such trip."""
        ...

    def find_by_date(self, service_date: str) -> list[Trip]:
        """Every materialized trip running on that date, in departure order."""
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

    def active_for_seat(self, trip_id: str, seat_id: str) -> list[Hold]:
        ...

    def active_for_passenger(self, trip_id: str, passenger_id: str) -> list[Hold]:
        ...

    def active_holds(self, trip_id: str) -> list[Hold]:
        """Every HELD/CONFIRMED hold on the trip. The occupancy for availability."""
        ...

    def by_status(self, trip_id: str, status: BookingStatus) -> list[Hold]:
        """Every booking on the trip in one status. Counts STANDING tickets, which are
        live but hold no seat, outside the active-occupancy queries."""
        ...

    def expire_due(self, now: int) -> list[Hold]:
        """Flip every HELD whose `held_until <= now` to EXPIRED; return them (D12)."""
        ...


class UnitOfWork(Protocol):
    bookings: BookingRepository
    trips: TripRepository

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
