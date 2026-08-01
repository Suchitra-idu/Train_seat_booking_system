"""The reserved booking lifecycle over HTTP (D6): quote, hold, confirm, cancel.

There is no public lookup-by-reference and no unreserved route (D23, D24). Reading a
booking back means holding the counter key, so a guessed reference cannot surface a
stranger's NIC; unreserved is sold at the window.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from slr.app.config import Settings
from slr.app.deps import get_deps, get_settings
from slr.app.schemas import (
    BookingOut,
    HoldRequest,
    MoneyOut,
    QuoteOut,
    QuoteRequest,
    ReceiptOut,
)
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.cancel_booking import cancel_booking
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat
from slr.usecases.quote_fare import quote_fare

router = APIRouter(tags=["bookings"])


@router.post("/quote", response_model=QuoteOut)
def quote(
    body: QuoteRequest,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> QuoteOut:
    fare = quote_fare(
        deps,
        trip_id=body.trip_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        travel_class=body.travel_class,
    )
    return QuoteOut(
        trip_id=body.trip_id,
        origin_seq=body.origin_seq,
        dest_seq=body.dest_seq,
        travel_class=body.travel_class,
        fare=MoneyOut.of(fare, settings.currency),
    )


@router.post("/bookings/hold", response_model=BookingOut, status_code=201)
def hold(
    body: HoldRequest,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> BookingOut:
    booking = hold_seat(
        deps,
        trip_id=body.trip_id,
        seat_id=body.seat_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        passenger_id=body.passenger_id,
        passenger_name=body.passenger_name,
        reference=body.reference,
    )
    return BookingOut.of(booking, settings.currency)


@router.post("/bookings/{booking_id}/confirm", response_model=ReceiptOut)
def confirm(
    booking_id: str,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> ReceiptOut:
    return ReceiptOut.of(confirm_booking(deps, booking_id=booking_id), settings.currency)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel(
    booking_id: str,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> BookingOut:
    return BookingOut.of(cancel_booking(deps, booking_id=booking_id), settings.currency)
