"""Read routes: search trips, per-leg availability, and the resale impact report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from slr.app.deps import get_deps
from slr.app.schemas import ImpactOut, LegAvailabilityOut, TripOut
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.impact_report import impact_report
from slr.usecases.leg_availability import leg_availability
from slr.usecases.search_trips import search_trips

router = APIRouter(tags=["trips"])


@router.get("/trips", response_model=list[TripOut])
def list_trips(
    route_code: str = Query(...),
    service_date: str = Query(...),
    deps: Deps = Depends(get_deps),
) -> list[TripOut]:
    trips = search_trips(deps, route_code=route_code, service_date=service_date)
    return [TripOut.of(t) for t in trips]


@router.get("/trips/{trip_id}/availability", response_model=LegAvailabilityOut)
def trip_availability(
    trip_id: str,
    origin_seq: int = Query(..., ge=0),
    dest_seq: int = Query(..., ge=0),
    deps: Deps = Depends(get_deps),
) -> LegAvailabilityOut:
    view = leg_availability(deps, trip_id=trip_id, leg=Leg(origin_seq, dest_seq))
    return LegAvailabilityOut.of(view)


@router.get("/trips/{trip_id}/impact", response_model=ImpactOut)
def trip_impact(trip_id: str, deps: Deps = Depends(get_deps)) -> ImpactOut:
    return ImpactOut.of(impact_report(deps, trip_id=trip_id))
