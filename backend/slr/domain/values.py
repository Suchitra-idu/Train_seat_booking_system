"""Cross-cutting value objects shared across domain modules.

Enums only — no fare multipliers or seat counts live here; those are config (D11)
and arrive as parameters so nothing is hardcoded in a rule.
"""

from __future__ import annotations

from enum import StrEnum


class BookingStatus(StrEnum):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class CoachType(StrEnum):
    RESERVED = "RESERVED"
    UNRESERVED = "UNRESERVED"


class TravelClass(StrEnum):
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"


#: Statuses that occupy a seat/leg — the scope of the overlap invariant (D2).
ACTIVE_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.HELD, BookingStatus.CONFIRMED}
)

#: Terminal statuses — no transition leaves them.
TERMINAL_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CANCELLED, BookingStatus.EXPIRED}
)
