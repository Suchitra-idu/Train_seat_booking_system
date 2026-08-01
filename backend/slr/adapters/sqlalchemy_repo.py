"""Postgres repository adapter (D2, D12).

Same contract as the in-memory fake, backed by the GiST EXCLUDE constraint. `add_hold`
inserts inside a savepoint so a constraint violation rolls back that one insert and
surfaces as `OverlapError`, leaving the surrounding transaction usable. `expire_due`
retires overdue holds lazily inside the caller's transaction.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from slr.adapters.orm import (
    BookingRow,
    TripRow,
    WaitlistRow,
    leg_to_range,
    range_to_leg,
)
from slr.domain.errors import OverlapError
from slr.domain.stations import Leg, Station
from slr.domain.values import ACTIVE_STATUSES, BookingStatus, CoachType, TravelClass
from slr.ports.repository import Hold, Seat, Trip, WaitlistEntry

_ACTIVE = [s.value for s in ACTIVE_STATUSES]


def _to_hold(row: BookingRow) -> Hold:
    return Hold(
        booking_id=row.booking_id,
        reference=row.reference,
        trip_id=row.trip_id,
        seat_id=row.seat_id or "",
        leg=range_to_leg(row.leg),
        passenger_id=row.passenger_id,
        travel_class=TravelClass(row.travel_class),
        status=BookingStatus(row.status),
        held_until=row.held_until,
        created_at=row.created_at,
    )


def _to_row(hold: Hold) -> BookingRow:
    return BookingRow(
        booking_id=hold.booking_id,
        reference=hold.reference,
        trip_id=hold.trip_id,
        seat_id=hold.seat_id or None,
        leg=leg_to_range(hold.leg),
        passenger_id=hold.passenger_id,
        travel_class=hold.travel_class.value,
        status=hold.status.value,
        held_until=hold.held_until,
        created_at=hold.created_at,
    )


def _to_trip(row: TripRow) -> Trip:
    stations = tuple(Station(**s) for s in row.stations)
    seats = tuple(
        Seat(
            seat_id=s["seat_id"],
            coach=s["coach"],
            coach_type=CoachType(s["coach_type"]),
            travel_class=TravelClass(s["travel_class"]),
            number=s["number"],
        )
        for s in row.seats
    )
    return Trip(row.trip_id, row.route_code, row.service_date, stations, seats)


def _to_waitlist(row: WaitlistRow) -> WaitlistEntry:
    return WaitlistEntry(
        waitlist_id=row.waitlist_id,
        trip_id=row.trip_id,
        leg=range_to_leg(row.leg),
        passenger_id=row.passenger_id,
        travel_class=TravelClass(row.travel_class),
        created_at=row.created_at,
    )


def _is_overlap_violation(err: IntegrityError) -> bool:
    diag = getattr(getattr(err, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None) == "booking_no_overlap"


class SqlAlchemyTripRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, trip_id: str) -> Trip:
        row = self._session.get(TripRow, trip_id)
        if row is None:
            raise KeyError(trip_id)
        return _to_trip(row)

    def find(self, route_code: str, service_date: str) -> list[Trip]:
        stmt = select(TripRow).where(
            TripRow.route_code == route_code, TripRow.service_date == service_date
        )
        return [_to_trip(r) for r in self._session.scalars(stmt)]


class SqlAlchemyBookingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_hold(self, hold: Hold) -> None:
        try:
            with self._session.begin_nested():
                self._session.add(_to_row(hold))
        except IntegrityError as err:
            if _is_overlap_violation(err):
                raise OverlapError(
                    f"seat {hold.seat_id} already held over {hold.leg} "
                    f"on trip {hold.trip_id}"
                ) from err
            raise

    def get(self, booking_id: str) -> Hold:
        row = self._session.get(BookingRow, booking_id)
        if row is None:
            raise KeyError(booking_id)
        return _to_hold(row)

    def by_reference(self, reference: str) -> Hold | None:
        stmt = select(BookingRow).where(BookingRow.reference == reference)
        row = self._session.scalars(stmt).first()
        return _to_hold(row) if row is not None else None

    def set_status(self, booking_id: str, status: BookingStatus) -> Hold:
        row = self._session.get(BookingRow, booking_id)
        if row is None:
            raise KeyError(booking_id)
        row.status = status.value
        self._session.flush()
        return _to_hold(row)

    def assign_seat(self, booking_id: str, seat_id: str) -> Hold:
        row = self._session.get(BookingRow, booking_id)
        if row is None:
            raise KeyError(booking_id)
        try:
            with self._session.begin_nested():
                row.seat_id = seat_id
                self._session.flush()
        except IntegrityError as err:
            if _is_overlap_violation(err):
                raise OverlapError(
                    f"seat {seat_id} already held over {range_to_leg(row.leg)} "
                    f"on trip {row.trip_id}"
                ) from err
            raise
        return _to_hold(row)

    def active_for_seat(self, trip_id: str, seat_id: str) -> list[Hold]:
        stmt = select(BookingRow).where(
            BookingRow.trip_id == trip_id,
            BookingRow.seat_id == seat_id,
            BookingRow.status.in_(_ACTIVE),
        )
        return [_to_hold(r) for r in self._session.scalars(stmt)]

    def active_for_passenger(self, trip_id: str, passenger_id: str) -> list[Hold]:
        stmt = select(BookingRow).where(
            BookingRow.trip_id == trip_id,
            BookingRow.passenger_id == passenger_id,
            BookingRow.status.in_(_ACTIVE),
        )
        return [_to_hold(r) for r in self._session.scalars(stmt)]

    def active_holds(self, trip_id: str) -> list[Hold]:
        stmt = select(BookingRow).where(
            BookingRow.trip_id == trip_id, BookingRow.status.in_(_ACTIVE)
        )
        return [_to_hold(r) for r in self._session.scalars(stmt)]

    def by_status(self, trip_id: str, status: BookingStatus) -> list[Hold]:
        stmt = select(BookingRow).where(
            BookingRow.trip_id == trip_id, BookingRow.status == status.value
        )
        return [_to_hold(r) for r in self._session.scalars(stmt)]

    def expire_due(self, now: int) -> list[Hold]:
        stmt = select(BookingRow).where(
            BookingRow.status == BookingStatus.HELD.value,
            BookingRow.held_until <= now,
        )
        expired: list[Hold] = []
        for row in self._session.scalars(stmt):
            row.status = BookingStatus.EXPIRED.value
            expired.append(_to_hold(row))
        self._session.flush()
        return expired


class SqlAlchemyWaitlistRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entry: WaitlistEntry) -> None:
        self._session.add(
            WaitlistRow(
                waitlist_id=entry.waitlist_id,
                trip_id=entry.trip_id,
                leg=leg_to_range(entry.leg),
                passenger_id=entry.passenger_id,
                travel_class=entry.travel_class.value,
                created_at=entry.created_at,
            )
        )
        self._session.flush()

    def next_compatible(
        self, trip_id: str, leg: Leg, travel_class: TravelClass
    ) -> WaitlistEntry | None:
        stmt = (
            select(WaitlistRow)
            .where(
                WaitlistRow.trip_id == trip_id,
                WaitlistRow.travel_class == travel_class.value,
                WaitlistRow.leg.op("<@")(leg_to_range(leg)),
            )
            .order_by(WaitlistRow.created_at, WaitlistRow.waitlist_id)
        )
        row = self._session.scalars(stmt).first()
        return _to_waitlist(row) if row is not None else None

    def remove(self, waitlist_id: str) -> None:
        row = self._session.get(WaitlistRow, waitlist_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def for_trip(self, trip_id: str) -> list[WaitlistEntry]:
        stmt = select(WaitlistRow).where(WaitlistRow.trip_id == trip_id)
        return [_to_waitlist(r) for r in self._session.scalars(stmt)]


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session = session_factory()
        self._committed = False
        self.bookings = SqlAlchemyBookingRepository(self._session)
        self.trips = SqlAlchemyTripRepository(self._session)
        self.waitlist = SqlAlchemyWaitlistRepository(self._session)

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            self._session.rollback()

    def commit(self) -> None:
        self._session.commit()
        self._committed = True

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


def insert_trip(session: Session, trip: Trip) -> None:
    """Seed a trip row (out of band, since TripRepository is read-only)."""
    session.add(
        TripRow(
            trip_id=trip.trip_id,
            route_code=trip.route_code,
            service_date=trip.service_date,
            stations=[
                {"code": s.code, "name": s.name, "seq": s.seq, "km": s.km}
                for s in trip.stations
            ],
            seats=[
                {
                    "seat_id": s.seat_id,
                    "coach": s.coach,
                    "coach_type": s.coach_type.value,
                    "travel_class": s.travel_class.value,
                    "number": s.number,
                }
                for s in trip.seats
            ],
        )
    )
    session.commit()
