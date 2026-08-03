"""make demo-resale: A->B and B->C on the *same* seat both succeed (D2, P7).

Segment resale is the headline guarantee: two non-overlapping legs never collide, so
one physical seat serves two passengers on the same trip. Spins a throwaway Postgres,
holds and confirms both legs through the real use-cases, and proves both land CONFIRMED
on the identical seat.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slr.adapters.fake_clock import FakeClock
from slr.adapters.fake_payment import FakePayment
from slr.adapters.fixed_fare import FixedFare
from slr.adapters.fixture_config import FixtureConfig
from slr.adapters.memory_notifier import MemoryNotifier
from slr.adapters.memory_publisher import MemoryPublisher
from slr.adapters.orm import create_schema
from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, upsert_trip
from slr.domain.fares import Money
from slr.domain.stations import Leg, Station
from slr.domain.timetable import Stop
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Coach, Seat, Trip
from slr.usecases._deps import Deps
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat

DEFAULT_CONFIG = {
    "hold_ttl_seconds": "900",
    "max_seats_per_passenger": "6",
    "velocity_window_seconds": "600",
    "max_bookings_per_window": "10",
    "abuse_threshold": "0.8",
    "standing_capacity_per_coach": "50",
    "class_mult_first": "2.0",
    "class_mult_second": "1.0",
    "class_mult_third": "0.7",
}


def _postgres():
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer
    return PostgresContainer("postgres:16-alpine", driver="psycopg")


def _trip() -> Trip:
    stations = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10)) for i in range(6)
    )
    stops = tuple(
        Stop(
            station_seq=i,
            arrive_min=None if i == 0 else 480 + i * 60,
            depart_min=None if i == 5 else 485 + i * 60,
        )
        for i in range(6)
    )
    return Trip(
        trip_id="trip-1",
        route_code="CMB-BAD",
        service_date="2026-08-01",
        train_no="1005",
        train_name="Demo Express",
        stations=stations,
        stops=stops,
        coaches=(Coach("C1", CoachType.RESERVED, TravelClass.SECOND, 1, "1-0"),),
        seats=(Seat("seat-1", "C1", CoachType.RESERVED, TravelClass.SECOND, 1, 1, "A"),),
    )


def main() -> None:
    with _postgres() as pg:
        engine = create_engine(pg.get_connection_url())
        create_schema(engine)
        factory = sessionmaker(bind=engine)
        seed = factory()
        upsert_trip(seed, _trip())
        seed.commit()
        seed.close()

        uow = SqlAlchemyUnitOfWork(factory)
        deps = Deps(
            uow=uow,
            clock=FakeClock(1_000),
            ids=SeqIdGen(),
            references=SeqReferenceGen(),
            fares=FixedFare(Money.rupees(100)),
            config=FixtureConfig(DEFAULT_CONFIG),
            notifier=MemoryNotifier(),
            availability=MemoryPublisher(),
            abuse=ScriptedAbuse(0.0),
            payment=FakePayment(),
        )

        fort_to_kandy = hold_seat(
            deps,
            trip_id="trip-1",
            seat_id="seat-1",
            leg=Leg(0, 2),
            passenger_id="p1",
            passenger_name="Ann Perera",
        )
        kandy_to_badulla = hold_seat(
            deps,
            trip_id="trip-1",
            seat_id="seat-1",
            leg=Leg(2, 5),
            passenger_id="p2",
            passenger_name="Nimal Silva",
        )
        confirm_booking(deps, booking_id=fort_to_kandy.booking_id)
        confirm_booking(deps, booking_id=kandy_to_badulla.booking_id)
        uow.close()
        engine.dispose()

    print(
        "same seat, two non-overlapping legs -> both CONFIRMED "
        f"({fort_to_kandy.reference} on [0,2), {kandy_to_badulla.reference} on [2,5))"
    )


if __name__ == "__main__":
    main()
