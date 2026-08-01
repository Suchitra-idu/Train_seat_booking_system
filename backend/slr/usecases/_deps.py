"""Dependency bundle handed to every use-case. Ports only, never adapters (D14)."""

from __future__ import annotations

from dataclasses import dataclass

from slr.ports.abuse import AbuseScorer
from slr.ports.availability import AvailabilityPublisher
from slr.ports.clock import Clock
from slr.ports.config import Config
from slr.ports.fares import FareStrategy
from slr.ports.ids import IdGen, ReferenceGen
from slr.ports.notifier import Notifier
from slr.ports.payment import PaymentGateway
from slr.ports.repository import UnitOfWork


@dataclass(frozen=True, slots=True)
class Deps:
    uow: UnitOfWork
    clock: Clock
    ids: IdGen
    references: ReferenceGen
    fares: FareStrategy
    config: Config
    notifier: Notifier
    availability: AvailabilityPublisher
    abuse: AbuseScorer
    payment: PaymentGateway
