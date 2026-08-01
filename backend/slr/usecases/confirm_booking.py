"""Confirm a reserved hold with online payment (D6). HELD to CONFIRMED, or fail clean."""

from __future__ import annotations

from slr.domain.booking_sm import BookingEvent, apply
from slr.domain.errors import BookingNotFound, PaymentDeclined
from slr.domain.fares import Money
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold, Trip
from slr.usecases._deps import Deps
from slr.usecases._support import (
    class_mult,
    leg_distance_km,
    occupancy_over_leg,
)


def confirm_booking(deps: Deps, *, booking_id: str) -> Hold:
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
        result = deps.payment.charge(hold.reference, _fare(deps, trip, hold))
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
        return confirmed


def _fare(deps: Deps, trip: Trip, hold: Hold) -> Money:
    return deps.fares.price(
        distance_km=leg_distance_km(trip, hold.leg),
        class_mult=class_mult(deps.config.get_float, hold.travel_class),
        occupancy=occupancy_over_leg(deps.uow, trip, hold.leg),
    )
