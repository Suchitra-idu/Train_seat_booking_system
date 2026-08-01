"""Reserved-coach hold: the passenger picks the seat (D6). Anti-tout gate, idempotent."""

from __future__ import annotations

from slr.domain.errors import SeatNotBookable
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold, Seat, Trip
from slr.usecases._deps import Deps
from slr.usecases._policy import enforce_anti_tout
from slr.usecases._support import HOLD_TTL, validate_leg


def _reserved_seat(trip: Trip, seat_id: str) -> Seat:
    seat = next((s for s in trip.seats if s.seat_id == seat_id), None)
    if seat is None or seat.coach_type is not CoachType.RESERVED:
        raise SeatNotBookable(f"seat {seat_id} is not a reservable seat on {trip.trip_id}")
    return seat


def hold_seat(
    deps: Deps,
    *,
    trip_id: str,
    seat_id: str,
    leg: Leg,
    passenger_id: str,
    travel_class: TravelClass,
    reference: str | None = None,
) -> Hold:
    now = deps.clock.now()
    with deps.uow as uow:
        bookings = uow.bookings
        if reference is not None:
            existing = bookings.by_reference(reference)
            if existing is not None:
                return existing  # idempotent replay, no second hold and no velocity hit

        bookings.expire_due(now)
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        _reserved_seat(trip, seat_id)
        enforce_anti_tout(deps, trip_id, passenger_id, now)

        hold = Hold(
            booking_id=deps.ids.new_id(),
            reference=reference or deps.references.new_reference(),
            trip_id=trip_id,
            seat_id=seat_id,
            leg=leg,
            passenger_id=passenger_id,
            travel_class=travel_class,
            status=BookingStatus.HELD,
            held_until=now + deps.config.get_int(HOLD_TTL),
            created_at=now,
        )
        bookings.add_hold(hold)  # raises OverlapError on a taken seat/leg (D2)
        deps.availability.publish(
            AvailabilityEvent(trip_id, seat_id, leg, BookingStatus.HELD)
        )
        deps.notifier.notify(
            passenger_id, "seat_held", {"reference": hold.reference, "seat_id": seat_id}
        )
        uow.commit()
        return hold
