"""Fake payment gateway. Always succeeds, or declines chosen references. Records charges."""

from __future__ import annotations

from collections.abc import Iterable

from slr.domain.fares import Money
from slr.ports.payment import PaymentResult


class FakePayment:
    def __init__(
        self, *, decline: bool = False, decline_refs: Iterable[str] = ()
    ) -> None:
        self._decline_all = decline
        self._decline_refs = set(decline_refs)
        self.charges: list[tuple[str, Money]] = []

    def charge(self, reference: str, amount: Money) -> PaymentResult:
        self.charges.append((reference, amount))
        declined = self._decline_all or reference in self._decline_refs
        return PaymentResult(
            ok=not declined,
            reference=reference,
            detail="declined" if declined else "",
        )
