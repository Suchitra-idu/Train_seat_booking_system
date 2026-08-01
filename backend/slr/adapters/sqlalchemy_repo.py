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

from slr.adapters.orm import BookingRow, TripRow, leg_to_range, range_to_leg
from slr.domain.errors import OverlapError
from slr.domain.stations import Station
from slr.domain.timetable import Stop, departure_min
from slr.domain.values import ACTIVE_STATUSES, BookingStatus, CoachType, TravelClass
from slr.ports.repository import (
    BookingRepository,
    Coach,
    Hold,
    Seat,
    Trip,
    TripRepository,
)

_ACTIVE = [s.value for s in ACTIVE_STATUSES]


def _to_hold(row: BookingRow) -> Hold:
    return Hold(
        booking_id=row.booking_id,
        reference=row.reference,
        trip_id=row.trip_id,
        seat_id=row.seat_id or "",
        leg=range_to_leg(row.leg),
        passenger_id=row.passenger_id,
        passenger_name=row.passenger_name,
        travel_class=TravelClass(row.travel_class),
        status=BookingStatus(row.status),
        fare_cents=row.fare_cents,
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
        passenger_name=hold.passenger_name,
        travel_class=hold.travel_class.value,
        status=hold.status.value,
        fare_cents=hold.fare_cents,
        held_until=hold.held_until,
        created_at=hold.created_at,
    )


def _to_trip(row: TripRow) -> Trip:
    return Trip(
        trip_id=row.trip_id,
        route_code=row.route_code,
        service_date=row.service_date,
        train_no=row.train_no,
        train_name=row.train_name,
        stations=tuple(Station(**s) for s in row.stations),
        stops=tuple(Stop(**s) for s in row.stops),
        coaches=tuple(
            Coach(
                code=c["code"],
                coach_type=CoachType(c["coach_type"]),
                travel_class=TravelClass(c["travel_class"]),
                rows=c["rows"],
                columns=c["columns"],
                exit_rows=tuple(c["exit_rows"]),
            )
            for c in row.coaches
        ),
        seats=tuple(
            Seat(
                seat_id=s["seat_id"],
                coach=s["coach"],
                coach_type=CoachType(s["coach_type"]),
                travel_class=TravelClass(s["travel_class"]),
                number=s["number"],
                row=s["row"],
                column=s["column"],
            )
            for s in row.seats
        ),
    )


def _trip_values(trip: Trip) -> dict:
    return {
        "trip_id": trip.trip_id,
        "route_code": trip.route_code,
        "service_date": trip.service_date,
        "train_no": trip.train_no,
        "train_name": trip.train_name,
        "departs_min": departure_min(trip.stops),
        "stations": [
            {"code": s.code, "name": s.name, "seq": s.seq, "km": s.km}
            for s in trip.stations
        ],
        "stops": [
            {
                "station_seq": s.station_seq,
                "arrive_min": s.arrive_min,
                "depart_min": s.depart_min,
            }
            for s in trip.stops
        ],
        "coaches": [
            {
                "code": c.code,
                "coach_type": c.coach_type.value,
                "travel_class": c.travel_class.value,
                "rows": c.rows,
                "columns": c.columns,
                "exit_rows": list(c.exit_rows),
            }
            for c in trip.coaches
        ],
        "seats": [
            {
                "seat_id": s.seat_id,
                "coach": s.coach,
                "coach_type": s.coach_type.value,
                "travel_class": s.travel_class.value,
                "number": s.number,
                "row": s.row,
                "column": s.column,
            }
            for s in trip.seats
        ],
    }


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

    def find_by_date(self, service_date: str) -> list[Trip]:
        stmt = (
            select(TripRow)
            .where(TripRow.service_date == service_date)
            .order_by(TripRow.departs_min, TripRow.trip_id)
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


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session = session_factory()
        self._committed = False
        self.bookings: BookingRepository = SqlAlchemyBookingRepository(self._session)
        self.trips: TripRepository = SqlAlchemyTripRepository(self._session)

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


def upsert_trip(session: Session, trip: Trip) -> bool:
    """Seed one materialized trip (out of band, since TripRepository is read-only).

    Returns True when the row was inserted. Re-seeding the same window is a no-op, which
    is what makes `docker compose up` idempotent (D22).
    """
    if session.get(TripRow, trip.trip_id) is not None:
        return False
    session.add(TripRow(**_trip_values(trip)))
    session.flush()
    return True
