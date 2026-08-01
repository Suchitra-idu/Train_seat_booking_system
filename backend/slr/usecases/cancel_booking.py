"""Cancel a booking; a freed seat/leg re-offers to the waitlist (D6, D16)."""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.booking_sm import BookingEvent, apply
from slr.domain.errors import BookingNotFound
from slr.domain.values import ACTIVE_STATUSES, BookingStatus
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold
from slr.usecases._deps import Deps
from slr.usecases._promote import promote_freed_segment


@dataclass(frozen=True, slots=True)
class CancelResult:
    cancelled: Hold
    promoted: Hold | None


def cancel_booking(deps: Deps, *, booking_id: str) -> CancelResult:
    now = deps.clock.now()
    with deps.uow as uow:
        bookings = uow.bookings
        try:
            hold = bookings.get(booking_id)
        except KeyError:
            raise BookingNotFound(booking_id) from None

        apply(hold.status, BookingEvent.CANCEL)  # guards double-cancel and terminal states
        cancelled = bookings.set_status(booking_id, BookingStatus.CANCELLED)

        promoted = None
        if hold.status in ACTIVE_STATUSES:  # a HELD/CONFIRMED cancel frees a seat/leg
            promoted = promote_freed_segment(
                deps, hold.trip_id, hold.leg, hold.seat_id, hold.travel_class, now
            )
            deps.availability.publish(
                AvailabilityEvent(
                    hold.trip_id, hold.seat_id, hold.leg, BookingStatus.CANCELLED
                )
            )

        deps.notifier.notify(
            hold.passenger_id, "booking_cancelled", {"reference": hold.reference}
        )
        uow.commit()
        return CancelResult(cancelled, promoted)
