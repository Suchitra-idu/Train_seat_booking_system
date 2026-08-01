"""Read a booking by reference or id. Used by the user app and the counter."""

from __future__ import annotations

from slr.domain.errors import BookingNotFound
from slr.ports.repository import Hold
from slr.usecases._deps import Deps


def lookup_booking(
    deps: Deps, *, reference: str | None = None, booking_id: str | None = None
) -> Hold:
    with deps.uow as uow:
        if reference is not None:
            hold = uow.bookings.by_reference(reference)
            if hold is None:
                raise BookingNotFound(reference)
            return hold
        if booking_id is not None:
            try:
                return uow.bookings.get(booking_id)
            except KeyError:
                raise BookingNotFound(booking_id) from None
        raise ValueError("lookup_booking needs a reference or a booking_id")
