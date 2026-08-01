"""Booking status machine (D6), pure transition guards, no clock.

Expiry-by-time and payment are use-case concerns; this module only says which status
changes are legal. Cancelled and expired are terminal, so double-cancel and
confirm-after-expiry fail loud with IllegalTransition (mapped to a clean 4xx in L4).
"""

from __future__ import annotations

from enum import StrEnum

from slr.domain.errors import IllegalTransition
from slr.domain.values import BookingStatus


class BookingEvent(StrEnum):
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    EXPIRE = "EXPIRE"


_TRANSITIONS: dict[tuple[BookingStatus, BookingEvent], BookingStatus] = {
    (BookingStatus.HELD, BookingEvent.CONFIRM): BookingStatus.CONFIRMED,
    (BookingStatus.HELD, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    (BookingStatus.HELD, BookingEvent.EXPIRE): BookingStatus.EXPIRED,
    (BookingStatus.CONFIRMED, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    # A standing ticket (D20) mirrors a hold's lifecycle. Counter payment confirms it.
    # It can also cancel or lapse. Seat promotion is a seat_id change with no event here.
    (BookingStatus.STANDING, BookingEvent.CONFIRM): BookingStatus.CONFIRMED,
    (BookingStatus.STANDING, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    (BookingStatus.STANDING, BookingEvent.EXPIRE): BookingStatus.EXPIRED,
}


def can_apply(current: BookingStatus, event: BookingEvent) -> bool:
    return (current, event) in _TRANSITIONS


def apply(current: BookingStatus, event: BookingEvent) -> BookingStatus:
    try:
        return _TRANSITIONS[(current, event)]
    except KeyError:
        raise IllegalTransition(f"cannot {event.value} a {current.value} booking") from None
