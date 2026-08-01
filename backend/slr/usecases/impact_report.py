"""Capacity unlocked by segment resale vs rigid whole-journey booking (D10)."""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.packing import impact_seat_km, min_seats
from slr.domain.stations import km_index
from slr.usecases._deps import Deps


@dataclass(frozen=True, slots=True)
class ImpactReport:
    trip_id: str
    active_legs: int
    seats_used: int
    seat_km_reclaimed: float


def impact_report(deps: Deps, *, trip_id: str) -> ImpactReport:
    with deps.uow as uow:
        trip = uow.trips.get(trip_id)
        legs = [h.leg for h in uow.bookings.active_holds(trip_id)]

    kms = [s.km for s in trip.stations]
    route_km = max(kms) - min(kms)
    return ImpactReport(
        trip_id=trip_id,
        active_legs=len(legs),
        seats_used=min_seats(legs),
        seat_km_reclaimed=impact_seat_km(legs, km_index(trip.stations), route_km),
    )
