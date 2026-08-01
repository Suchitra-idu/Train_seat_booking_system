"""Read one materialized trip: its stations, calling times, coaches and seats.

The seat map needs the coach geometry (D25) once; availability over a leg is a separate,
repeated read. Splitting them keeps the live query small.
"""

from __future__ import annotations

from slr.ports.repository import Trip
from slr.usecases._deps import Deps


def get_trip(deps: Deps, *, trip_id: str) -> Trip:
    """Raises KeyError if no such trip, which L4 maps to 404."""
    with deps.uow as uow:
        return uow.trips.get(trip_id)
