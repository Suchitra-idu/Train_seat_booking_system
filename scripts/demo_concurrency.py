"""make demo-concurrency: fire N holds at one seat and leg, show exactly one wins (D2).

Spins a throwaway Postgres, seeds one trip and seat, then races N threads at the same
leg. The GiST EXCLUDE lets one commit and forces the rest to OverlapError (a 409).
"""

from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slr.adapters.orm import create_schema
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, upsert_trip
from slr.domain.errors import OverlapError
from slr.domain.stations import Leg, Station
from slr.domain.timetable import Stop
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.repository import Coach, Hold, Seat, Trip

N = 10


def _postgres():
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer
    return PostgresContainer("postgres:16-alpine", driver="psycopg")


def _trip() -> Trip:
    stations = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10))
        for i in range(6)
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


def _hold(i: int) -> Hold:
    return Hold(
        booking_id=f"b{i}",
        reference=f"SLR-{i:06d}",
        trip_id="trip-1",
        seat_id="seat-1",
        leg=Leg(0, 3),
        passenger_id=f"p{i}",
        passenger_name=f"Passenger {i}",
        travel_class=TravelClass.SECOND,
        status=BookingStatus.HELD,
        fare_cents=10_000,
        held_until=1_000,
        created_at=0,
    )


def main() -> None:
    with _postgres() as pg:
        engine = create_engine(pg.get_connection_url(), pool_size=N + 5)
        create_schema(engine)
        factory = sessionmaker(bind=engine)
        seed = factory()
        upsert_trip(seed, _trip())
        seed.commit()
        seed.close()

        barrier = threading.Barrier(N)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            uow = SqlAlchemyUnitOfWork(factory)
            try:
                with uow:
                    barrier.wait()
                    try:
                        uow.bookings.add_hold(_hold(i))
                        uow.commit()
                        result = "booked"
                    except OverlapError:
                        result = "409"
            finally:
                uow.close()
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        engine.dispose()

    booked = outcomes.count("booked")
    conflicts = outcomes.count("409")
    print(f"{N} threads raced one seat/leg -> {booked} booked, {conflicts} got 409")


if __name__ == "__main__":
    main()
