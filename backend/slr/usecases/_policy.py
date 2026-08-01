"""Anti-tout gate shared by the reserved and unreserved booking paths (D9).

Caps and velocity are hard config limits. The abuse score is a soft signal behind the
AbuseScorer seam; thresholding lives here, never in the score itself.
"""

from __future__ import annotations

from slr.domain.abuse import AbuseFeatures
from slr.domain.errors import AbuseSuspected, SeatCapExceeded, VelocityExceeded
from slr.usecases._deps import Deps
from slr.usecases._support import (
    ABUSE_THRESHOLD,
    MAX_BOOKINGS_PER_WINDOW,
    MAX_SEATS_PER_PASSENGER,
    VELOCITY_WINDOW,
)


def enforce_anti_tout(deps: Deps, trip_id: str, passenger_id: str, now: int) -> None:
    bookings = deps.uow.bookings
    active = bookings.active_for_passenger(trip_id, passenger_id)

    cap = deps.config.get_int(MAX_SEATS_PER_PASSENGER)
    if len(active) >= cap:
        raise SeatCapExceeded(f"{passenger_id} already holds {len(active)} seats (cap {cap})")

    window = deps.config.get_int(VELOCITY_WINDOW)
    limit = deps.config.get_int(MAX_BOOKINGS_PER_WINDOW)
    recent = [h for h in active if h.created_at > now - window]
    if len(recent) >= limit:
        raise VelocityExceeded(f"{passenger_id} booked {len(recent)} times in {window}s")

    features = AbuseFeatures(
        velocity=len(recent),
        passenger_fanout=1,
        seat_fanout=len({h.seat_id for h in active if h.seat_id}),
        cancel_ratio=0.0,
    )
    score = deps.abuse.score(features)
    if score >= deps.config.get_float(ABUSE_THRESHOLD):
        raise AbuseSuspected(f"risk {score:.2f} for {passenger_id}")
