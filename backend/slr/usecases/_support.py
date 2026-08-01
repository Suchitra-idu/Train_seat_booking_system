"""Shared read helpers: config keys, distance, occupancy, fares, leg validation."""

from __future__ import annotations

from slr.domain.errors import InvalidLeg
from slr.domain.fares import Money
from slr.domain.stations import Leg, km_index
from slr.domain.values import TravelClass
from slr.ports.repository import Trip, UnitOfWork
from slr.usecases._deps import Deps

# Config keys (D11). Nothing about caps, fares, windows, or TTLs is hardcoded in a rule.
HOLD_TTL = "hold_ttl_seconds"
MAX_SEATS_PER_PASSENGER = "max_seats_per_passenger"
VELOCITY_WINDOW = "velocity_window_seconds"
MAX_BOOKINGS_PER_WINDOW = "max_bookings_per_window"
ABUSE_THRESHOLD = "abuse_threshold"
STANDING_CAPACITY = "standing_capacity_per_coach"
BOOKING_WINDOW_DAYS = "booking_window_days"
UTC_OFFSET_MINUTES = "utc_offset_minutes"


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


def class_mult(deps: Deps, travel_class: TravelClass) -> float:
    return deps.config.get_float(f"class_mult_{travel_class.value.lower()}")


def price_leg(
    deps: Deps, uow: UnitOfWork, trip: Trip, leg: Leg, travel_class: TravelClass
) -> Money:
    """The one place a leg is priced (D4). Quote, hold and counter sale all go through it,
    so what the passenger is shown is what the passenger is charged."""
    return deps.fares.price(
        distance_km=leg_distance_km(trip, leg),
        class_mult=class_mult(deps, travel_class),
        occupancy=occupancy_over_leg(uow, trip, leg),
    )
