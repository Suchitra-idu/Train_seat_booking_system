"""Fare-strategy port. Price one leg from its distance, class, and live occupancy."""

from __future__ import annotations

from typing import Protocol

from slr.domain.fares import Money


class FareStrategy(Protocol):
    def price(self, *, distance_km: float, class_mult: float, occupancy: float) -> Money:
        ...
