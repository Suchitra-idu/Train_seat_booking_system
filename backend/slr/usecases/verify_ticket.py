"""Verify a ticket at the gate (D21). Read-only, by reference or scanned QR.

The QR carries the bare reference (D24), so this lookup is what makes a forged code fail:
the server either has the booking or it does not. The inspector gets back the NIC the
ticket is named for, which is the whole point of the Aug-2025 named-ticket policy (D8),
an ID rule nobody can check is not a rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from slr.domain.errors import BookingNotFound
from slr.domain.values import BookingStatus
from slr.usecases._deps import Deps
from slr.usecases._receipt import Receipt, receipt_for


class Verdict(StrEnum):
    VALID = "VALID"
    #: Held but never paid for: the passenger walked out mid-checkout.
    UNPAID = "UNPAID"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


_VERDICTS: dict[BookingStatus, Verdict] = {
    BookingStatus.CONFIRMED: Verdict.VALID,
    BookingStatus.STANDING: Verdict.VALID,
    BookingStatus.HELD: Verdict.UNPAID,
    BookingStatus.CANCELLED: Verdict.CANCELLED,
    BookingStatus.EXPIRED: Verdict.EXPIRED,
}


@dataclass(frozen=True, slots=True)
class Verification:
    verdict: Verdict
    receipt: Receipt

    @property
    def valid(self) -> bool:
        return self.verdict is Verdict.VALID


def verify_ticket(deps: Deps, *, reference: str) -> Verification:
    """Raises BookingNotFound (404) when no such reference exists, which is itself the
    answer for a forged or mistyped code."""
    now = deps.clock.now()
    with deps.uow as uow:
        uow.bookings.expire_due(now)
        booking = uow.bookings.by_reference(reference)
        if booking is None:
            raise BookingNotFound(reference)
        trip = uow.trips.get(booking.trip_id)
        uow.commit()
    return Verification(_VERDICTS[booking.status], receipt_for(booking, trip, issued_at=now))
