"""Distance fare strategy (D4). Prices a leg by distance and class. Occupancy is ignored."""

from __future__ import annotations

from slr.domain.fares import Money, distance_fare


class DistanceFare:
    def __init__(self, rate_per_km: Money) -> None:
        self._rate = rate_per_km

    def price(self, *, distance_km: float, class_mult: float, occupancy: float) -> Money:
        return distance_fare(distance_km, self._rate, class_mult)
