"""Fare arithmetic (D4): distance baseline * class * demand, all as exact money.

`fare = rate_per_km · km · class_mult · demand_mult`. Money is integer minor units
(LKR cents); the float multipliers are applied through Decimal and rounded half-up so
the result is deterministic and cent-exact. Segment resale (D2) is what lets this price
each leg fairly instead of charging the ~2x whole-journey penalty.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True, order=True)
class Money:
    cents: int

    @classmethod
    def rupees(cls, rupees: int) -> Money:
        return cls(rupees * 100)

    def __add__(self, other: Money) -> Money:
        return Money(self.cents + other.cents)

    def __mul__(self, qty: int) -> Money:
        return Money(self.cents * qty)


def _round_cents(value: Decimal) -> Money:
    return Money(int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


def distance_fare(distance_km: float, rate_per_km: Money, class_mult: float) -> Money:
    cents = Decimal(rate_per_km.cents) * Decimal(str(distance_km)) * Decimal(str(class_mult))
    return _round_cents(cents)


def demand_multiplier(occupancy: float, *, floor: float, ceiling: float) -> float:
    if ceiling < floor:
        raise ValueError(f"demand band inverted: floor={floor} > ceiling={ceiling}")
    clamped = min(1.0, max(0.0, occupancy))
    return floor + (ceiling - floor) * clamped


def dynamic_fare(
    distance_km: float,
    rate_per_km: Money,
    class_mult: float,
    *,
    occupancy: float,
    floor: float,
    ceiling: float,
) -> Money:
    base = distance_fare(distance_km, rate_per_km, class_mult)
    mult = demand_multiplier(occupancy, floor=floor, ceiling=ceiling)
    return _round_cents(Decimal(base.cents) * Decimal(str(mult)))
