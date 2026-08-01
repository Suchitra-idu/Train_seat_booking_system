"""Waitlist join and manual promotion of a freed segment (D16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from slr.app.deps import get_deps
from slr.app.schemas import BookingOut, PromoteRequest, WaitlistOut, WaitlistRequest
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.join_waitlist import join_waitlist
from slr.usecases.promote_waitlist import promote_waitlist

router = APIRouter(tags=["waitlist"])


@router.post("/waitlist", response_model=WaitlistOut, status_code=201)
def join(body: WaitlistRequest, deps: Deps = Depends(get_deps)) -> WaitlistOut:
    entry = join_waitlist(
        deps,
        trip_id=body.trip_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        passenger_id=body.passenger_id,
        travel_class=body.travel_class,
    )
    return WaitlistOut.of(entry)


@router.post("/waitlist/promote", response_model=BookingOut | None)
def promote(body: PromoteRequest, deps: Deps = Depends(get_deps)) -> BookingOut | None:
    promoted = promote_waitlist(
        deps,
        trip_id=body.trip_id,
        freed_leg=Leg(body.origin_seq, body.dest_seq),
        seat_id=body.seat_id,
        travel_class=body.travel_class,
    )
    return BookingOut.of(promoted) if promoted is not None else None
