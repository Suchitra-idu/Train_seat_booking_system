"""Booking lifecycle over HTTP: quote, hold (reserved), confirm, cancel, lookup, and the
unreserved NIC-only booking. The hold/confirm/cancel path is the reserved D6 lifecycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from slr.app.deps import get_deps
from slr.app.schemas import (
    BookingOut,
    CancelOut,
    HoldRequest,
    MoneyOut,
    QuoteOut,
    QuoteRequest,
    UnreservedRequest,
)
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.book_unreserved import book_unreserved
from slr.usecases.cancel_booking import cancel_booking
from slr.usecases.confirm_booking import confirm_booking
from slr.usecases.hold_seat import hold_seat
from slr.usecases.lookup_booking import lookup_booking
from slr.usecases.quote_fare import quote_fare

router = APIRouter(tags=["bookings"])


@router.post("/quote", response_model=QuoteOut)
def quote(body: QuoteRequest, deps: Deps = Depends(get_deps)) -> QuoteOut:
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
        fare=MoneyOut.of(fare),
    )


@router.post("/bookings/hold", response_model=BookingOut, status_code=201)
def hold(body: HoldRequest, deps: Deps = Depends(get_deps)) -> BookingOut:
    booking = hold_seat(
        deps,
        trip_id=body.trip_id,
        seat_id=body.seat_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        passenger_id=body.passenger_id,
        travel_class=body.travel_class,
        reference=body.reference,
    )
    return BookingOut.of(booking)


@router.post("/unreserved", response_model=BookingOut, status_code=201)
def unreserved(body: UnreservedRequest, deps: Deps = Depends(get_deps)) -> BookingOut:
    booking = book_unreserved(
        deps,
        trip_id=body.trip_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        passenger_id=body.passenger_id,
        travel_class=body.travel_class,
    )
    return BookingOut.of(booking)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingOut)
def confirm(booking_id: str, deps: Deps = Depends(get_deps)) -> BookingOut:
    return BookingOut.of(confirm_booking(deps, booking_id=booking_id))


@router.post("/bookings/{booking_id}/cancel", response_model=CancelOut)
def cancel(booking_id: str, deps: Deps = Depends(get_deps)) -> CancelOut:
    return CancelOut.of(cancel_booking(deps, booking_id=booking_id))


@router.get("/bookings/{reference}", response_model=BookingOut)
def lookup(reference: str, deps: Deps = Depends(get_deps)) -> BookingOut:
    return BookingOut.of(lookup_booking(deps, reference=reference))
