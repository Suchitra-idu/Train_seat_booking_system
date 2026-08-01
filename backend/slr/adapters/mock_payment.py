"""Mock payment gateway (D17). Approves every charge. No real money, no secrets."""

from __future__ import annotations

from slr.domain.fares import Money
from slr.ports.payment import PaymentResult


class MockPayment:
    def charge(self, reference: str, amount: Money) -> PaymentResult:
        return PaymentResult(ok=True, reference=reference)
