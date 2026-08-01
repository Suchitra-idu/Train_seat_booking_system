"""Sell an unreserved ticket at the counter (D21, D23). One transaction, cash taken.

Unreserved exists only here: the clerk takes the NIC and the journey, takes the money, and
the system assigns a hidden seat by the packing optimizer (D10) or issues standing with the
"sit on seat X after station Y" prediction (D20). The booking is created already paid, so
there is no unpaid intent occupying capacity and nothing to settle later.
"""

from __future__ import annotations

from slr.domain.errors import CoachFull, PaymentDeclined, SeatNotBookable
from slr.domain.packing import SeatOffer, choose_seat, predict_standing_seats
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.availability import AvailabilityEvent
from slr.ports.repository import Hold, Seat, Trip
from slr.usecases._deps import Deps
from slr.usecases._policy import enforce_anti_tout
from slr.usecases._receipt import Receipt, build_receipt
from slr.usecases._support import STANDING_CAPACITY, price_leg, validate_leg


def sell_unreserved(
    deps: Deps,
    *,
    trip_id: str,
    leg: Leg,
    passenger_id: str,
    passenger_name: str,
    travel_class: TravelClass,
    reference: str | None = None,
) -> Receipt:
    now = deps.clock.now()
    with deps.uow as uow:
        bookings = uow.bookings
        if reference is not None:
            existing = bookings.by_reference(reference)
            if existing is not None:
                trip = uow.trips.get(existing.trip_id)
                seat = next(
                    (s for s in trip.seats if s.seat_id == existing.seat_id), None
                )
                return build_receipt(existing, trip, issued_at=now, seat=seat)

        bookings.expire_due(now)
        trip = uow.trips.get(trip_id)
        validate_leg(trip, leg)
        enforce_anti_tout(deps, trip_id, passenger_id, now)

        pool = _pool(trip, travel_class)
        if not pool:
            raise SeatNotBookable(
                f"train {trip.train_no} has no unreserved "
                f"{travel_class.value} coach"
            )
        seat_legs = [
            [h.leg for h in bookings.active_for_seat(trip_id, s.seat_id)] for s in pool
        ]
        chosen = choose_seat(seat_legs, leg)

        offer: SeatOffer | None = None
        if chosen is None:
            _guard_standing_capacity(deps, trip_id, travel_class)
            offer = predict_standing_seats(seat_legs, [leg])[0]

        fare = price_leg(deps, uow, trip, leg, travel_class)
        ticket_ref = reference or deps.references.new_reference()
        result = deps.payment.charge(ticket_ref, fare)
        if not result.ok:
            raise PaymentDeclined(result.detail or "counter charge declined")

        seat = pool[chosen] if chosen is not None else None
        sold = Hold(
            booking_id=deps.ids.new_id(),
            reference=ticket_ref,
            trip_id=trip_id,
            seat_id=seat.seat_id if seat is not None else "",
            leg=leg,
            passenger_id=passenger_id,
            passenger_name=passenger_name,
            travel_class=travel_class,
            status=(
                BookingStatus.CONFIRMED if seat is not None else BookingStatus.STANDING
            ),
            fare_cents=fare.cents,
            held_until=0,  # a paid ticket never expires
            created_at=now,
        )
        bookings.add_hold(sold)  # still raises OverlapError if the seat was just taken

        if seat is not None:
            deps.availability.publish(
                AvailabilityEvent(trip_id, seat.seat_id, leg, sold.status)
            )
        deps.notifier.notify(
            passenger_id,
            "counter_sale",
            {"reference": sold.reference, "status": sold.status.value},
        )
        uow.commit()
        return build_receipt(sold, trip, issued_at=now, seat=seat, offer=offer, pool=pool)


def _pool(trip: Trip, travel_class: TravelClass) -> list[Seat]:
    return [
        s
        for s in trip.seats
        if s.coach_type is CoachType.UNRESERVED and s.travel_class is travel_class
    ]


def _guard_standing_capacity(
    deps: Deps, trip_id: str, travel_class: TravelClass
) -> None:
    standing = [
        h
        for h in deps.uow.bookings.by_status(trip_id, BookingStatus.STANDING)
        if h.travel_class is travel_class
    ]
    if len(standing) >= deps.config.get_int(STANDING_CAPACITY):
        raise CoachFull(f"unreserved {travel_class.value} coach is full")
