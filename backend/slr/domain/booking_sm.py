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
    STAND = "STAND"
    CANCEL = "CANCEL"
    EXPIRE = "EXPIRE"


_TRANSITIONS: dict[tuple[BookingStatus, BookingEvent], BookingStatus] = {
    (BookingStatus.HELD, BookingEvent.CONFIRM): BookingStatus.CONFIRMED,
    (BookingStatus.HELD, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    (BookingStatus.HELD, BookingEvent.EXPIRE): BookingStatus.EXPIRED,
    (BookingStatus.CONFIRMED, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    # Unreserved settles at the counter (D21). Paid with a seat gives CONFIRMED, paid with
    # a full coach gives STANDING. Unpaid intent cancels or lapses.
    (BookingStatus.PENDING, BookingEvent.CONFIRM): BookingStatus.CONFIRMED,
    (BookingStatus.PENDING, BookingEvent.STAND): BookingStatus.STANDING,
    (BookingStatus.PENDING, BookingEvent.CANCEL): BookingStatus.CANCELLED,
    (BookingStatus.PENDING, BookingEvent.EXPIRE): BookingStatus.EXPIRED,
    # A standing passenger takes a seat when one frees (D20).
    (BookingStatus.STANDING, BookingEvent.CONFIRM): BookingStatus.CONFIRMED,
    (BookingStatus.STANDING, BookingEvent.CANCEL): BookingStatus.CANCELLED,
}


def can_apply(current: BookingStatus, event: BookingEvent) -> bool:
    return (current, event) in _TRANSITIONS


def apply(current: BookingStatus, event: BookingEvent) -> BookingStatus:
    try:
        return _TRANSITIONS[(current, event)]
    except KeyError:
        raise IllegalTransition(f"cannot {event.value} a {current.value} booking") from None
