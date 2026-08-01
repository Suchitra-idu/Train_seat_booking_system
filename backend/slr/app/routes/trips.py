"""Read routes: search the timetable, read a trip, per-leg availability, impact report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from slr.app.config import Settings
from slr.app.deps import get_deps, get_settings
from slr.app.schemas import ImpactOut, LegAvailabilityOut, TrainOptionOut, TripOut
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.get_trip import get_trip
from slr.usecases.impact_report import impact_report
from slr.usecases.leg_availability import leg_availability
from slr.usecases.search_trains import search_trains

router = APIRouter(tags=["trips"])


@router.get("/search", response_model=list[TrainOptionOut])
def search(
    origin: str = Query(..., min_length=1, max_length=16),
    dest: str = Query(..., min_length=1, max_length=16),
    date: str = Query(..., min_length=10, max_length=10),
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> list[TrainOptionOut]:
    options = search_trains(deps, origin_code=origin, dest_code=dest, service_date=date)
    return [TrainOptionOut.of(o, settings.currency) for o in options]


@router.get("/trips/{trip_id}", response_model=TripOut)
def read_trip(trip_id: str, deps: Deps = Depends(get_deps)) -> TripOut:
    return TripOut.of(get_trip(deps, trip_id=trip_id))


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
