"""Fixed-price fare strategy. Returns a constant Money."""

from __future__ import annotations

from slr.domain.fares import Money


class FixedFare:
    def __init__(self, amount: Money) -> None:
        self._amount = amount

    def price(self, *, distance_km: float, class_mult: float, occupancy: float) -> Money:
        return self._amount
