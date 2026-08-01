"""Concurrency proof (D2). N transactions race one seat and leg; the GiST EXCLUDE lets
exactly one commit and forces the rest to OverlapError. Adjacent legs never contend.
"""

import threading

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, insert_trip
from slr.domain.errors import OverlapError
from slr.domain.stations import Leg, Station
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.repository import Hold, Seat, Trip


def _trip():
    stations = tuple(
        Station(code=f"S{i}", name=f"Station {i}", seq=i, km=float(i * 10))
        for i in range(6)
    )
    seats = (Seat("seat-1", "C1", CoachType.RESERVED, TravelClass.SECOND, 1),)
    return Trip("trip-1", "CMB-BAD", "2026-08-01", stations, seats)


def _hold(booking_id, leg):
    return Hold(
        booking_id=booking_id,
        reference=f"ref-{booking_id}",
        trip_id="trip-1",
        seat_id="seat-1",
        leg=leg,
        passenger_id=booking_id,
        travel_class=TravelClass.SECOND,
        status=BookingStatus.HELD,
        held_until=1_000,
        created_at=0,
    )


def _reset_and_seed(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE booking, waitlist, trip"))
    seed = sessionmaker(bind=engine)()
    insert_trip(seed, _trip())
    seed.close()


def _race(engine, legs_by_worker):
    """Fire every worker at one barrier; return the list of outcomes."""
    factory = sessionmaker(bind=engine)
    n = len(legs_by_worker)
    barrier = threading.Barrier(n)
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(i, leg):
        uow = SqlAlchemyUnitOfWork(factory)
        try:
            with uow:
                barrier.wait()
                try:
                    uow.bookings.add_hold(_hold(f"b{i}", leg))
                    uow.commit()
                    outcome = "booked"
                except OverlapError:
                    outcome = "conflict"
        finally:
            uow.close()
        with lock:
            outcomes.append(outcome)

    threads = [
        threading.Thread(target=worker, args=(i, leg))
        for i, leg in enumerate(legs_by_worker)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return outcomes


@pytest.mark.concurrency
def test_n_concurrent_holds_on_one_leg_yield_exactly_one_winner(postgres_engine):
    _reset_and_seed(postgres_engine)
    n = 10
    outcomes = _race(postgres_engine, [Leg(0, 3)] * n)
    assert outcomes.count("booked") == 1
    assert outcomes.count("conflict") == n - 1


@pytest.mark.concurrency
def test_adjacent_legs_commit_concurrently_without_conflict(postgres_engine):
    _reset_and_seed(postgres_engine)
    # [0,2), [2,4), [4,6): three non-overlapping legs on one seat, all commit.
    outcomes = _race(postgres_engine, [Leg(0, 2), Leg(2, 4), Leg(4, 6)])
    assert outcomes == ["booked", "booked", "booked"]
