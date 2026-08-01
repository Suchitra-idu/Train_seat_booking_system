"""Payment port. A decline is a normal result with ok=False, never an exception."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from slr.domain.fares import Money


@dataclass(frozen=True, slots=True)
class PaymentResult:
    ok: bool
    reference: str
    detail: str = ""


class PaymentGateway(Protocol):
    def charge(self, reference: str, amount: Money) -> PaymentResult:
        ...
