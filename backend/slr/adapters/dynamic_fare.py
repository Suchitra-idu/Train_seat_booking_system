"""Dynamic fare strategy (D4). Distance fare scaled by an occupancy demand band."""

from __future__ import annotations

from slr.domain.fares import Money, dynamic_fare


class DynamicFare:
    def __init__(
        self, rate_per_km: Money, *, floor: float = 1.0, ceiling: float = 1.8
    ) -> None:
        self._rate = rate_per_km
        self._floor = floor
        self._ceiling = ceiling

    def price(self, *, distance_km: float, class_mult: float, occupancy: float) -> Money:
        return dynamic_fare(
            distance_km,
            self._rate,
            class_mult,
            occupancy=occupancy,
            floor=self._floor,
            ceiling=self._ceiling,
        )
