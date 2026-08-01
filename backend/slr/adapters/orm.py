"""SQLAlchemy schema for the persistence adapter (D2, D19).

The overlap invariant is the partial GiST EXCLUDE on `booking`: no two active holds may
share a trip and seat over overlapping legs. btree_gist supplies the `=` operators for
trip_id and seat_id inside a gist index. Trip stations and seats ride as JSONB, since
they are seeded config (D11) and never queried on their own.
"""

from __future__ import annotations

from psycopg.types.range import Range
from sqlalchemy import Integer, String, text
from sqlalchemy.dialects.postgresql import INT4RANGE, JSONB, ExcludeConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from slr.domain.stations import Leg


class Base(DeclarativeBase):
    pass


class TripRow(Base):
    __tablename__ = "trip"

    trip_id: Mapped[str] = mapped_column(String, primary_key=True)
    route_code: Mapped[str] = mapped_column(String, index=True)
    service_date: Mapped[str] = mapped_column(String, index=True)
    stations: Mapped[list] = mapped_column(JSONB)
    seats: Mapped[list] = mapped_column(JSONB)


class BookingRow(Base):
    __tablename__ = "booking"

    booking_id: Mapped[str] = mapped_column(String, primary_key=True)
    reference: Mapped[str] = mapped_column(String, index=True)
    trip_id: Mapped[str] = mapped_column(String, index=True)
    seat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    leg: Mapped[Range] = mapped_column(INT4RANGE)
    passenger_id: Mapped[str] = mapped_column(String, index=True)
    travel_class: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    held_until: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        ExcludeConstraint(
            ("trip_id", "="),
            ("seat_id", "="),
            ("leg", "&&"),
            using="gist",
            where=text("status IN ('HELD','CONFIRMED')"),
            name="booking_no_overlap",
        ),
    )


class WaitlistRow(Base):
    __tablename__ = "waitlist"

    waitlist_id: Mapped[str] = mapped_column(String, primary_key=True)
    trip_id: Mapped[str] = mapped_column(String, index=True)
    leg: Mapped[Range] = mapped_column(INT4RANGE)
    passenger_id: Mapped[str] = mapped_column(String)
    travel_class: Mapped[str] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer)


def leg_to_range(leg: Leg) -> Range:
    return Range(leg.origin_seq, leg.dest_seq, bounds="[)")


def range_to_leg(value: Range) -> Leg:
    lower, upper = value.lower, value.upper
    assert lower is not None and upper is not None  # int4range is always bounded here
    return Leg(lower, upper)


def create_schema(engine: Engine) -> None:
    """Build the schema on a fresh database: the extension first, then the tables and the
    EXCLUDE constraint. Mirrors the Alembic migration used for real bring-up (D19)."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    Base.metadata.create_all(engine)
