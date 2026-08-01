"""Dependency wiring for the composition root — the one place real adapters are injected.

A `Container` holds the singleton adapters (clock, ids, fares, config, notifier, the SSE
publisher, abuse, payment) and a `uow_factory`. Each HTTP request calls `deps()` for a
fresh `Deps` with its own UnitOfWork (its own DB session), so requests never share a
transaction. Use-cases still see ports only (D14); the framework never reaches them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slr.adapters.distance_fare import DistanceFare
from slr.adapters.dynamic_fare import DynamicFare
from slr.adapters.fake_clock import FakeClock
from slr.adapters.fake_payment import FakePayment
from slr.adapters.fixed_fare import FixedFare
from slr.adapters.fixture_config import FixtureConfig
from slr.adapters.heuristic_abuse import HeuristicAbuse
from slr.adapters.log_notifier import LogNotifier
from slr.adapters.memory_repo import MemoryUnitOfWork
from slr.adapters.mock_payment import MockPayment
from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen
from slr.adapters.sqlalchemy_repo import SqlAlchemyUnitOfWork
from slr.adapters.sse_publisher import SsePublisher
from slr.adapters.system_clock import SystemClock
from slr.adapters.uuid_ids import UuidIdGen, UuidReferenceGen
from slr.app.config import Settings, build_config
from slr.domain.fares import Money
from slr.ports.abuse import AbuseScorer
from slr.ports.clock import Clock
from slr.ports.config import Config
from slr.ports.fares import FareStrategy
from slr.ports.ids import IdGen, ReferenceGen
from slr.ports.notifier import Notifier
from slr.ports.payment import PaymentGateway
from slr.ports.repository import Trip, UnitOfWork
from slr.usecases._deps import Deps


@dataclass(frozen=True, slots=True)
class Container:
    uow_factory: Callable[[], UnitOfWork]
    clock: Clock
    ids: IdGen
    references: ReferenceGen
    fares: FareStrategy
    config: Config
    notifier: Notifier
    availability: SsePublisher
    abuse: AbuseScorer
    payment: PaymentGateway

    def deps(self) -> Deps:
        return Deps(
            uow=self.uow_factory(),
            clock=self.clock,
            ids=self.ids,
            references=self.references,
            fares=self.fares,
            config=self.config,
            notifier=self.notifier,
            availability=self.availability,
            abuse=self.abuse,
            payment=self.payment,
        )


def _fare_strategy(settings: Settings) -> FareStrategy:
    rate = Money(settings.fare_rate_per_km_cents)
    if settings.fare_strategy == "distance":
        return DistanceFare(rate)
    return DynamicFare(rate)


def wire_real(
    settings: Settings, *, session_factory: sessionmaker | None = None
) -> Container:
    if session_factory is None:
        engine = create_engine(settings.database_url)
        session_factory = sessionmaker(bind=engine)
    return Container(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        clock=SystemClock(),
        ids=UuidIdGen(),
        references=UuidReferenceGen(),
        fares=_fare_strategy(settings),
        config=build_config(settings),
        notifier=LogNotifier(),
        availability=SsePublisher(),
        abuse=HeuristicAbuse(),
        payment=MockPayment(),
    )


# Config the fake container serves so the use-cases' policy reads resolve (D11 keys).
_FAKE_POLICY: dict[str, str] = {
    "hold_ttl_seconds": "900",
    "pending_ttl_seconds": "3600",
    "max_seats_per_passenger": "4",
    "velocity_window_seconds": "600",
    "max_bookings_per_window": "3",
    "abuse_threshold": "0.8",
    "standing_capacity_per_coach": "2",
    "class_mult_first": "2.0",
    "class_mult_second": "1.0",
    "class_mult_third": "0.7",
}


def wire_fake(
    trips: tuple[Trip, ...] = (),
    *,
    start: int = 1_000,
    fare: Money | None = None,
    decline: bool = False,
    abuse_default: float = 0.0,
) -> Container:
    """An all-fake, infra-free Container. Drives the contract tests and OpenAPI emission,
    where the HTTP surface matters and the backing store does not."""
    uow = MemoryUnitOfWork(trips=trips)
    return Container(
        uow_factory=lambda: uow,
        clock=FakeClock(start),
        ids=SeqIdGen(),
        references=SeqReferenceGen(),
        fares=FixedFare(fare if fare is not None else Money(10_000)),
        config=FixtureConfig(_FAKE_POLICY),
        notifier=LogNotifier(),
        availability=SsePublisher(),
        abuse=ScriptedAbuse(abuse_default),
        payment=FakePayment(decline=decline),
    )
