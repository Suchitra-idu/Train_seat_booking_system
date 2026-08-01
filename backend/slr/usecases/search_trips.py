"""Find trips on a route and service date."""

from __future__ import annotations

from slr.ports.repository import Trip
from slr.usecases._deps import Deps


def search_trips(deps: Deps, *, route_code: str, service_date: str) -> list[Trip]:
    with deps.uow as uow:
        return uow.trips.find(route_code, service_date)
