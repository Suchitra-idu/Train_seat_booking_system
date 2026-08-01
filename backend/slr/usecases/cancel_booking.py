"""Cancel a booking. The freed segment reopens immediately (D6).

Cancelling takes the row out of the EXCLUDE constraint's scope, so the leg is bookable
again the instant the transaction commits, and the SSE delta tells every watching client.
There is no waiting queue to promote into: D16 was withdrawn.
"""

from __future__ import annotations

from slr.domain.booking_sm import BookingEvent, apply
from slr.domain.errors import BookingNotFound
from slr.domain.values import ACTIVE_STATUSES, BookingStatus
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold
from slr.usecases._deps import Deps


def cancel_booking(deps: Deps, *, booking_id: str) -> Hold:
    with deps.uow as uow:
        bookings = uow.bookings
        try:
            hold = bookings.get(booking_id)
        except KeyError:
            raise BookingNotFound(booking_id) from None

        apply(hold.status, BookingEvent.CANCEL)  # guards double-cancel and terminal states
        cancelled = bookings.set_status(booking_id, BookingStatus.CANCELLED)

        if hold.status in ACTIVE_STATUSES:  # a HELD/CONFIRMED cancel frees a seat/leg
            deps.availability.publish(
                AvailabilityEvent(
                    hold.trip_id, hold.seat_id, hold.leg, BookingStatus.CANCELLED
                )
            )

        deps.notifier.notify(
            hold.passenger_id, "booking_cancelled", {"reference": hold.reference}
        )
        uow.commit()
        return cancelled
