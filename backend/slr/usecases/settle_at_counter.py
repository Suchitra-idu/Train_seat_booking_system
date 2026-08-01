"""Counter settlement of an unreserved PENDING ticket (D21).

The counter enters the reference, the system assigns a seat by the packing optimizer
(D10) or issues standing when the coach is full (D20), takes the cash charge, transitions
PENDING to CONFIRMED or STANDING, and returns an invoice.
"""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.booking_sm import BookingEvent, apply
from slr.domain.errors import (
    BookingNotFound,
    CoachFull,
    IllegalTransition,
    PaymentDeclined,
)
from slr.domain.fares import Money
from slr.domain.packing import SeatOffer, choose_seat, predict_standing_seats
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, CoachType
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold, Seat, Trip
from slr.usecases._deps import Deps
from slr.usecases._support import (
    STANDING_CAPACITY,
    class_mult,
    leg_distance_km,
    occupancy_over_leg,
)


@dataclass(frozen=True, slots=True)
class Invoice:
    reference: str
    passenger_id: str
    trip_id: str
    service_date: str
    leg: Leg
    fare: Money
    status: BookingStatus
    issued_at: int
    seat_id: str | None = None
    #: standing prediction (D20): "sit on seat `standing_seat` after station `standing_after`".
    standing_after: int | None = None
    standing_seat: int | None = None


def settle_at_counter(deps: Deps, *, reference: str) -> Invoice:
    now = deps.clock.now()
    with deps.uow as uow:
        bookings = uow.bookings
        pending = bookings.by_reference(reference)
        if pending is None:
            raise BookingNotFound(reference)
        if pending.status is not BookingStatus.PENDING:
            raise IllegalTransition(f"{reference} is {pending.status.value}, not PENDING")

        trip = uow.trips.get(pending.trip_id)
        pool = [
            s
            for s in trip.seats
            if s.coach_type is CoachType.UNRESERVED
            and s.travel_class == pending.travel_class
        ]
        seat_legs = [
            [h.leg for h in bookings.active_for_seat(trip.trip_id, s.seat_id)] for s in pool
        ]
        chosen = choose_seat(seat_legs, pending.leg)

        offer = None
        if chosen is None:
            standing = [
                h
                for h in bookings.by_status(trip.trip_id, BookingStatus.STANDING)
                if h.travel_class == pending.travel_class
            ]
            if len(standing) >= deps.config.get_int(STANDING_CAPACITY):
                raise CoachFull(f"unreserved {pending.travel_class.value} coach is full")
            offer = predict_standing_seats(seat_legs, [pending.leg])[0]

        fare = _unreserved_fare(deps, trip, pending)
        result = deps.payment.charge(reference, fare)
        if not result.ok:
            raise PaymentDeclined(result.detail or "counter charge declined")

        if chosen is not None:
            seat = pool[chosen]
            bookings.assign_seat(pending.booking_id, seat.seat_id)
            settled = bookings.set_status(
                pending.booking_id, apply(pending.status, BookingEvent.CONFIRM)
            )
            deps.availability.publish(
                AvailabilityEvent(trip.trip_id, seat.seat_id, pending.leg, settled.status)
            )
            invoice = _invoice(pending, trip, fare, settled.status, now, seat=seat)
        else:
            settled = bookings.set_status(
                pending.booking_id, apply(pending.status, BookingEvent.STAND)
            )
            invoice = _invoice(pending, trip, fare, settled.status, now, offer=offer, pool=pool)

        deps.notifier.notify(
            pending.passenger_id,
            "counter_settled",
            {"reference": reference, "status": settled.status.value},
        )
        uow.commit()
        return invoice


def _unreserved_fare(deps: Deps, trip: Trip, pending: Hold) -> Money:
    return deps.fares.price(
        distance_km=leg_distance_km(trip, pending.leg),
        class_mult=class_mult(deps.config.get_float, pending.travel_class),
        occupancy=occupancy_over_leg(deps.uow, trip, pending.leg),
    )


def _invoice(
    pending: Hold,
    trip: Trip,
    fare: Money,
    status: BookingStatus,
    now: int,
    *,
    seat: Seat | None = None,
    offer: SeatOffer | None = None,
    pool: list[Seat] | None = None,
) -> Invoice:
    standing_after = offer.board_seq if offer is not None else None
    standing_seat = (
        pool[offer.seat_index].number if offer is not None and pool is not None else None
    )
    return Invoice(
        reference=pending.reference,
        passenger_id=pending.passenger_id,
        trip_id=trip.trip_id,
        service_date=trip.service_date,
        leg=pending.leg,
        fare=fare,
        status=status,
        issued_at=now,
        seat_id=seat.seat_id if seat is not None else None,
        standing_after=standing_after,
        standing_seat=standing_seat,
    )
