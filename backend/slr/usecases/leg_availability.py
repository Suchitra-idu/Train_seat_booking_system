"""Per-seat availability over a requested leg. Retires expired holds first (D12)."""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases._deps import Deps
from slr.usecases._support import validate_leg


@dataclass(frozen=True, slots=True)
class SeatAvailability:
    seat_id: str
    coach: str
    travel_class: TravelClass
    available: bool


@dataclass(frozen=True, slots=True)
class LegAvailability:
    trip_id: str
    leg: Leg
    seats: tuple[SeatAvailability, ...]
    free_count: int


def leg_availability(deps: Deps, *, trip_id: str, leg: Leg) -> LegAvailability:
    with deps.uow as uow:
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        uow.bookings.expire_due(deps.clock.now())

        busy: dict[str, list[Leg]] = {}
        for hold in uow.bookings.active_holds(trip_id):
            busy.setdefault(hold.seat_id, []).append(hold.leg)

        seats = tuple(
            SeatAvailability(
                seat_id=s.seat_id,
                coach=s.coach,
                travel_class=s.travel_class,
                available=not any(other.overlaps(leg) for other in busy.get(s.seat_id, [])),
            )
            for s in trip.seats
        )
        uow.commit()

    free_count = sum(1 for s in seats if s.available)
    return LegAvailability(trip_id, leg, seats, free_count)
