"""Thin real pass: drive hold and confirm through the actual Postgres repository, so the
overlap constraint and transaction wiring are exercised end to end, not just the fake.
"""

import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, make_trip

from slr.adapters.fake_clock import FakeClock
from slr.adapters.fake_payment import FakePayment
from slr.adapters.fixed_fare import FixedFare
from slr.adapters.fixture_config import FixtureConfig
from slr.adapters.memory_notifier import MemoryNotifier
from slr.adapters.memory_publisher import MemoryPublisher
from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork, upsert_trip
from slr.domain.errors import OverlapError
from slr.domain.fares import Money
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.usecases._deps import Deps
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat


@pytest.fixture
def real_deps(pg_session_factory):
    seed = pg_session_factory()
    upsert_trip(seed, make_trip())
    seed.commit()
    seed.close()
    uow = SqlAlchemyUnitOfWork(pg_session_factory)
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
    yield deps
    uow.close()


_LEG = Leg(0, 3)


def _hold(deps, seat_id="R1", leg=_LEG, passenger="p1"):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id=passenger,
        passenger_name="Ann Perera",
    )


@pytest.mark.integration
def test_hold_then_confirm_on_real_postgres(real_deps):
    hold = _hold(real_deps)
    confirmed = confirm_booking(real_deps, booking_id=hold.booking_id)
    assert confirmed.status is BookingStatus.CONFIRMED
    assert real_deps.uow.bookings.get(hold.booking_id).status is BookingStatus.CONFIRMED


@pytest.mark.integration
def test_overlapping_hold_is_rejected_by_the_constraint(real_deps):
    _hold(real_deps, leg=Leg(0, 3), passenger="p1")
    with pytest.raises(OverlapError):
        _hold(real_deps, leg=Leg(1, 2), passenger="p2")


@pytest.mark.integration
def test_segment_resale_adjacent_legs_on_the_same_seat_both_confirm(real_deps):
    """The signature journey (D2): A->B and B->C don't overlap, so the same physical
    seat serves both passengers, proven against the real GiST constraint, not a fake."""
    first = _hold(real_deps, leg=Leg(0, 2), passenger="p1")
    second = _hold(real_deps, leg=Leg(2, 3), passenger="p2")

    confirm_booking(real_deps, booking_id=first.booking_id)
    confirm_booking(real_deps, booking_id=second.booking_id)

    assert real_deps.uow.bookings.get(first.booking_id).status is BookingStatus.CONFIRMED
    assert real_deps.uow.bookings.get(second.booking_id).status is BookingStatus.CONFIRMED
