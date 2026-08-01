"""Waitlist promotion on a freed segment (D16). Runs inside the caller's transaction."""

from __future__ import annotations

from slr.domain.errors import OverlapError
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold
from slr.usecases._deps import Deps
from slr.usecases._support import HOLD_TTL


def promote_freed_segment(
    deps: Deps,
    trip_id: str,
    freed_leg: Leg,
    seat_id: str,
    travel_class: TravelClass,
    now: int,
) -> Hold | None:
    """Offer the freed seat to the oldest compatible waiter. FIFO, first that fits."""
    waitlist = deps.uow.waitlist
    entry = waitlist.next_compatible(trip_id, freed_leg, travel_class)
    if entry is None:
        return None

    hold = Hold(
        booking_id=deps.ids.new_id(),
        reference=deps.references.new_reference(),
        trip_id=trip_id,
        seat_id=seat_id,
        leg=entry.leg,
        passenger_id=entry.passenger_id,
        travel_class=travel_class,
        status=BookingStatus.HELD,
        held_until=now + deps.config.get_int(HOLD_TTL),
        created_at=now,
    )
    try:
        deps.uow.bookings.add_hold(hold)
    except OverlapError:
        return None

    waitlist.remove(entry.waitlist_id)
    deps.notifier.notify(
        entry.passenger_id,
        "waitlist_promoted",
        {"reference": hold.reference, "seat_id": seat_id},
    )
    deps.availability.publish(
        AvailabilityEvent(trip_id, seat_id, entry.leg, BookingStatus.HELD)
    )
    return hold
