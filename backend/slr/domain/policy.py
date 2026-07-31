"""Anti-tout policy predicates (D9), pure over history + injected `now`.

Caps and velocity limits are config (D11) and passed in; `now` and booking timestamps
are epoch seconds handed down from the Clock port, so nothing here reads a wall clock.
Nonsensical configuration (zero window, negative limit/cap) fails loud rather than
silently mis-policing.
"""

from __future__ import annotations

from collections.abc import Sequence


def within_seat_cap(active_count: int, requested: int, cap: int) -> bool:
    """True if a passenger holding `active_count` seats may take `requested` more."""
    if requested < 1:
        raise ValueError(f"requested seats must be >= 1, got {requested}")
    if cap < 0 or active_count < 0:
        raise ValueError("cap and active_count must be non-negative")
    return active_count + requested <= cap


def within_velocity(
    booking_times: Sequence[int], now: int, *, window_seconds: int, limit: int
) -> bool:
    """True if another booking is allowed given bookings in the trailing window.

    The window `(now - window_seconds, now]` is half-open at the old end: a booking
    exactly `window_seconds` old has aged out.
    """
    if window_seconds <= 0:
        raise ValueError(f"window_seconds must be > 0, got {window_seconds}")
    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")
    cutoff = now - window_seconds
    recent = sum(1 for t in booking_times if cutoff < t <= now)
    return recent < limit


def named_passenger_ok(ticket_id: str, boarding_id: str) -> bool:
    """True if the boarding ID matches the ticket's named passenger (non-transferable)."""
    a = ticket_id.strip().casefold()
    b = boarding_id.strip().casefold()
    return bool(a) and a == b
