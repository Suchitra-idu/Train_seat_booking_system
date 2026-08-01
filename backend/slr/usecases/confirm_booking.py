"""Confirm a reserved hold with online payment (D6). HELD to CONFIRMED, or fail clean.

Charges the fare fixed when the seat was held, so a demand swing between picking a seat
and paying cannot change the price under the passenger. Returns the receipt (D24), the
same shape the counter prints for an unreserved ticket.
"""

from __future__ import annotations

from slr.domain.booking_sm import BookingEvent, apply
from slr.domain.errors import BookingNotFound, PaymentDeclined
from slr.domain.fares import Money
from slr.ports.availability import AvailabilityEvent
from slr.usecases._deps import Deps
from slr.usecases._receipt import Receipt, receipt_for


def confirm_booking(deps: Deps, *, booking_id: str) -> Receipt:
    now = deps.clock.now()
    with deps.uow as uow:
        bookings = uow.bookings
        bookings.expire_due(now)
        try:
            hold = bookings.get(booking_id)
        except KeyError:
            raise BookingNotFound(booking_id) from None

        # Guard the transition before charging: an expired or terminal hold fails here.
        target = apply(hold.status, BookingEvent.CONFIRM)

        trip = uow.trips.get(hold.trip_id)
        result = deps.payment.charge(hold.reference, Money(hold.fare_cents))
        if not result.ok:
            raise PaymentDeclined(result.detail or "charge declined")

        confirmed = bookings.set_status(booking_id, target)
        deps.availability.publish(
            AvailabilityEvent(hold.trip_id, hold.seat_id, hold.leg, confirmed.status)
        )
        deps.notifier.notify(
            hold.passenger_id, "booking_confirmed", {"reference": hold.reference}
        )
        uow.commit()
        return receipt_for(confirmed, trip, issued_at=now)
