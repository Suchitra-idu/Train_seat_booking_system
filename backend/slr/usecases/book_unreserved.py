"""Unreserved NIC-only booking (D3). No seat picker, no online pay: a PENDING ticket
with a reference/QR, settled at the counter (D21). Same anti-tout gate as reserved.
"""

from __future__ import annotations

from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, TravelClass
from slr.ports.repository import Hold
from slr.usecases._deps import Deps
from slr.usecases._policy import enforce_anti_tout
from slr.usecases._support import PENDING_TTL, validate_leg


def book_unreserved(
    deps: Deps,
    *,
    trip_id: str,
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
                return existing

        bookings.expire_due(now)
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        enforce_anti_tout(deps, trip_id, passenger_id, now)

        pending = Hold(
            booking_id=deps.ids.new_id(),
            reference=reference or deps.references.new_reference(),
            trip_id=trip_id,
            seat_id="",
            leg=leg,
            passenger_id=passenger_id,
            travel_class=travel_class,
            status=BookingStatus.PENDING,
            held_until=now + deps.config.get_int(PENDING_TTL),
            created_at=now,
        )
        bookings.add_hold(pending)
        deps.notifier.notify(
            passenger_id,
            "unreserved_booked",
            {"reference": pending.reference, "action": "pay_at_counter"},
        )
        uow.commit()
        return pending
