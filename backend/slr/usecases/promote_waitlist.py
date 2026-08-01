"""Promote the oldest compatible waiter onto a freed segment (D16)."""

from __future__ import annotations

from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.ports.repository import Hold
from slr.usecases._deps import Deps
from slr.usecases._promote import promote_freed_segment


def promote_waitlist(
    deps: Deps,
    *,
    trip_id: str,
    freed_leg: Leg,
    seat_id: str,
    travel_class: TravelClass,
) -> Hold | None:
    now = deps.clock.now()
    with deps.uow as uow:
        promoted = promote_freed_segment(
            deps, trip_id, freed_leg, seat_id, travel_class, now
        )
        uow.commit()
        return promoted
