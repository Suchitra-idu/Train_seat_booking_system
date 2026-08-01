"""The ticket receipt (D24), one shape for both channels.

A reserved seat bought in the app and an unreserved ticket bought at the window produce
the *same* record, so there is one contract shape, one view-model, and one screen for the
inspector to read. The QR payload is the bare reference: verification is an online lookup
against the server, which is the only party that knows whether a booking exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.fares import Money
from slr.domain.packing import SeatOffer
from slr.domain.stations import Station
from slr.domain.timetable import format_hhmm, leg_times
from slr.domain.values import BookingStatus, TravelClass
from slr.ports.repository import Hold, Seat, Trip


@dataclass(frozen=True, slots=True)
class StandingAdvice:
    """D20's prediction, printed on a standing ticket: a seat frees at this station."""

    after_seq: int
    after_station: str
    seat_label: str


@dataclass(frozen=True, slots=True)
class Receipt:
    reference: str
    qr_payload: str
    passenger_id: str
    passenger_name: str
    booking_id: str
    trip_id: str
    route_code: str
    train_no: str
    train_name: str
    service_date: str
    origin_code: str
    origin_name: str
    origin_seq: int
    dest_code: str
    dest_name: str
    dest_seq: int
    depart: str
    arrive: str
    duration_min: int
    travel_class: TravelClass
    fare: Money
    status: BookingStatus
    issued_at: int
    coach: str | None = None
    seat_label: str | None = None
    standing: StandingAdvice | None = None


def seat_label(seat: Seat) -> str:
    return f"{seat.row}{seat.column}"


def _station(trip: Trip, seq: int) -> Station:
    return next(s for s in trip.stations if s.seq == seq)


def build_receipt(
    hold: Hold,
    trip: Trip,
    *,
    issued_at: int,
    seat: Seat | None = None,
    offer: SeatOffer | None = None,
    pool: list[Seat] | None = None,
) -> Receipt:
    """Assemble the receipt for a paid booking. `seat` is set for a seated ticket;
    `offer` and `pool` carry the standing prediction for a standing one."""
    times = leg_times(trip.stops, hold.leg)
    origin = _station(trip, hold.leg.origin_seq)
    dest = _station(trip, hold.leg.dest_seq)

    advice = None
    if offer is not None and pool is not None:
        advice = StandingAdvice(
            after_seq=offer.board_seq,
            after_station=_station(trip, offer.board_seq).name,
            seat_label=seat_label(pool[offer.seat_index]),
        )

    return Receipt(
        reference=hold.reference,
        qr_payload=hold.reference,
        passenger_id=hold.passenger_id,
        passenger_name=hold.passenger_name,
        booking_id=hold.booking_id,
        trip_id=trip.trip_id,
        route_code=trip.route_code,
        train_no=trip.train_no,
        train_name=trip.train_name,
        service_date=trip.service_date,
        origin_code=origin.code,
        origin_name=origin.name,
        origin_seq=origin.seq,
        dest_code=dest.code,
        dest_name=dest.name,
        dest_seq=dest.seq,
        depart=format_hhmm(times.depart_min),
        arrive=format_hhmm(times.arrive_min),
        duration_min=times.duration_min,
        travel_class=hold.travel_class,
        fare=Money(hold.fare_cents),
        status=hold.status,
        issued_at=issued_at,
        coach=seat.coach if seat is not None else None,
        seat_label=seat_label(seat) if seat is not None else None,
        standing=advice,
    )


def receipt_for(hold: Hold, trip: Trip, *, issued_at: int) -> Receipt:
    """Receipt for an existing booking, resolving its seat from the trip."""
    seat = next((s for s in trip.seats if s.seat_id == hold.seat_id), None)
    return build_receipt(hold, trip, issued_at=issued_at, seat=seat)
