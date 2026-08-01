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
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Seat, Trip
from slr.usecases._deps import Deps

DEFAULT_CONFIG = {
    "hold_ttl_seconds": 900,
    "pending_ttl_seconds": 3600,
    "max_seats_per_passenger": 4,
    "velocity_window_seconds": 600,
    "max_bookings_per_window": 3,
    "abuse_threshold": 0.8,
    "standing_capacity_per_coach": 2,
    "class_mult_first": 2.0,
    "class_mult_second": 1.0,
    "class_mult_third": 0.7,
}

START = 1_000
_DEFAULT_FARE = Money.rupees(100)


def make_trip(
    trip_id: str = "trip-1",
    *,
    reserved: int = 3,
    unreserved: int = 2,
    stations: int = 6,
    travel_class: TravelClass = TravelClass.SECOND,
) -> Trip:
    stops = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10))
        for i in range(stations)
    )
    seats = tuple(
        Seat(f"R{i + 1}", "R1", CoachType.RESERVED, travel_class, i + 1)
        for i in range(reserved)
    ) + tuple(
        Seat(f"U{i + 1}", "U1", CoachType.UNRESERVED, travel_class, i + 1)
        for i in range(unreserved)
    )
    return Trip(trip_id, "CMB-BAD", "2026-08-01", stops, seats)


def build(
    *,
    trip: Trip | None = None,
    config: dict | None = None,
    abuse_default: float = 0.0,
    abuse_scores: tuple[float, ...] = (),
    decline: bool = False,
    fare: Money = _DEFAULT_FARE,
) -> Deps:
    trip = trip or make_trip()
    return Deps(
        uow=MemoryUnitOfWork(trips=[trip]),
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
