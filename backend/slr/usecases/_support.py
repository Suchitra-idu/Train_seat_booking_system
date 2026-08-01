"""Shared read helpers: config keys, distance, occupancy, leg validation."""

from __future__ import annotations

from collections.abc import Callable

from slr.domain.errors import InvalidLeg
from slr.domain.stations import Leg, km_index
from slr.domain.values import TravelClass
from slr.ports.repository import Trip, UnitOfWork

# Config keys (D11). Nothing about caps, fares, or TTLs is hardcoded in a rule.
HOLD_TTL = "hold_ttl_seconds"
PENDING_TTL = "pending_ttl_seconds"
MAX_SEATS_PER_PASSENGER = "max_seats_per_passenger"
VELOCITY_WINDOW = "velocity_window_seconds"
MAX_BOOKINGS_PER_WINDOW = "max_bookings_per_window"
ABUSE_THRESHOLD = "abuse_threshold"
STANDING_CAPACITY = "standing_capacity_per_coach"


def validate_leg(trip: Trip, leg: Leg) -> None:
    seqs = {s.seq for s in trip.stations}
    if leg.origin_seq not in seqs or leg.dest_seq not in seqs:
        raise InvalidLeg(f"leg {leg} runs off trip {trip.trip_id}'s station sequence")


def leg_distance_km(trip: Trip, leg: Leg) -> float:
    return leg.distance_km(km_index(trip.stations))


def occupancy_over_leg(uow: UnitOfWork, trip: Trip, leg: Leg) -> float:
    """Fraction of the trip's seats actively held over any part of the leg."""
    if not trip.seats:
        return 0.0
    busy = {
        h.seat_id
        for h in uow.bookings.active_holds(trip.trip_id)
        if h.leg.overlaps(leg)
    }
    return len(busy) / len(trip.seats)


def class_mult(get_float: Callable[[str], float], travel_class: TravelClass) -> float:
    return get_float(f"class_mult_{travel_class.value.lower()}")
