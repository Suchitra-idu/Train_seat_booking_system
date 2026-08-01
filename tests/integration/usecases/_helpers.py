"""Fake wiring for use-case tests: an all-fake Deps and a configurable trip.

All-fake keeps these fast and deterministic, so concurrency and error semantics are
pinned without infrastructure (P4 doctrine). A thin real pass lives in test_real_pass.py.
"""

from __future__ import annotations

from slr.adapters.fake_clock import FakeClock
from slr.adapters.fake_payment import FakePayment
from slr.adapters.fixed_fare import FixedFare
from slr.adapters.fixture_config import FixtureConfig
from slr.adapters.memory_notifier import MemoryNotifier
from slr.adapters.memory_publisher import MemoryPublisher
from slr.adapters.memory_repo import MemoryUnitOfWork
from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen
from slr.domain.fares import Money
from slr.domain.stations import Station
from slr.domain.timetable import Stop
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Coach, Seat, Trip
from slr.usecases._deps import Deps

DEFAULT_CONFIG = {
    "hold_ttl_seconds": 900,
    "max_seats_per_passenger": 4,
    "velocity_window_seconds": 600,
    "max_bookings_per_window": 3,
    "abuse_threshold": 0.8,
    "standing_capacity_per_coach": 2,
    "booking_window_days": 30,
    "utc_offset_minutes": 0,
    "class_mult_first": 2.0,
    "class_mult_second": 1.0,
    "class_mult_third": 0.7,
}

#: FakeClock's epoch, and the date it falls on with utc_offset_minutes=0.
START = 1_000
TODAY = "1970-01-01"
_DEFAULT_FARE = Money.rupees(100)


def make_trip(
    trip_id: str = "trip-1",
    *,
    reserved: int = 3,
    unreserved: int = 2,
    stations: int = 6,
    travel_class: TravelClass = TravelClass.SECOND,
    service_date: str = TODAY,
    train_no: str = "1005",
    train_name: str = "Test Express",
    skip_stops: tuple[int, ...] = (),
) -> Trip:
    """A trip with one reserved and one unreserved coach, one seat per row.

    `skip_stops` are station sequences the train passes without calling at, which is what
    makes "this train does not serve your journey" testable.
    """
    stops = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10))
        for i in range(stations)
    )
    calls = tuple(
        Stop(
            station_seq=i,
            arrive_min=None if i == 0 else 480 + i * 60,
            depart_min=None if i == stations - 1 else 485 + i * 60,
        )
        for i in range(stations)
        if i not in skip_stops
    )
    coaches = tuple(
        Coach(code, coach_type, travel_class, rows, "1-0")
        for code, coach_type, rows in (
            ("R1", CoachType.RESERVED, reserved),
            ("U1", CoachType.UNRESERVED, unreserved),
        )
        if rows > 0
    )
    seats = tuple(
        Seat(f"R{i + 1}", "R1", CoachType.RESERVED, travel_class, i + 1, i + 1, "A")
        for i in range(reserved)
    ) + tuple(
        Seat(f"U{i + 1}", "U1", CoachType.UNRESERVED, travel_class, i + 1, i + 1, "A")
        for i in range(unreserved)
    )
    return Trip(
        trip_id=trip_id,
        route_code="CMB-BAD",
        service_date=service_date,
        train_no=train_no,
        train_name=train_name,
        stations=stops,
        stops=calls,
        coaches=coaches,
        seats=seats,
    )


def build(
    *,
    trip: Trip | None = None,
    trips: list[Trip] | None = None,
    config: dict | None = None,
    abuse_default: float = 0.0,
    abuse_scores: tuple[float, ...] = (),
    decline: bool = False,
    fare: Money = _DEFAULT_FARE,
) -> Deps:
    seeded = trips if trips is not None else [trip or make_trip()]
    return Deps(
        uow=MemoryUnitOfWork(trips=seeded),
        clock=FakeClock(START),
        ids=SeqIdGen(),
        references=SeqReferenceGen(),
        fares=FixedFare(fare),
        config=FixtureConfig(config or DEFAULT_CONFIG),
        notifier=MemoryNotifier(),
        availability=MemoryPublisher(),
        abuse=ScriptedAbuse(abuse_default, abuse_scores),
        payment=FakePayment(decline=decline),
    )
