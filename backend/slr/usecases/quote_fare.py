"""Price one leg: distance baseline, class multiplier, live demand (D4)."""

from __future__ import annotations

from slr.domain.fares import Money
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases._deps import Deps
from slr.usecases._support import (
    class_mult,
    leg_distance_km,
    occupancy_over_leg,
    validate_leg,
)


def quote_fare(
    deps: Deps, *, trip_id: str, leg: Leg, travel_class: TravelClass
) -> Money:
    with deps.uow as uow:
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        return deps.fares.price(
            distance_km=leg_distance_km(trip, leg),
            class_mult=class_mult(deps.config.get_float, travel_class),
            occupancy=occupancy_over_leg(uow, trip, leg),
        )
