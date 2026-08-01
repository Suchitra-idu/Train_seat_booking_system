"""Join the waitlist for a leg that has no free seat now (D16)."""

from __future__ import annotations

from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.ports.repository import WaitlistEntry
from slr.usecases._deps import Deps
from slr.usecases._support import validate_leg


def join_waitlist(
    deps: Deps,
    *,
    trip_id: str,
    leg: Leg,
    passenger_id: str,
    travel_class: TravelClass,
) -> WaitlistEntry:
    now = deps.clock.now()
    with deps.uow as uow:
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        entry = WaitlistEntry(
            waitlist_id=deps.ids.new_id(),
            trip_id=trip_id,
            leg=leg,
            passenger_id=passenger_id,
            travel_class=travel_class,
            created_at=now,
        )
        uow.waitlist.add(entry)
        uow.commit()
        return entry
