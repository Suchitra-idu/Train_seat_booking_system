"""The API contract, as Pydantic models (D13). FastAPI turns these into the OpenAPI
schema the frontend generates its client from, and the same models validate responses at
runtime on both sides of the seam. `from_*` builders map domain/use-case results in.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from slr.domain.fares import Money
from slr.domain.stations import Station
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.repository import Hold, Seat, Trip, WaitlistEntry
from slr.usecases.cancel_booking import CancelResult
from slr.usecases.impact_report import ImpactReport
from slr.usecases.leg_availability import LegAvailability
from slr.usecases.settle_at_counter import Invoice


class ErrorResponse(BaseModel):
    error: str
    detail: str


class MoneyOut(BaseModel):
    cents: int
    currency: str = "LKR"

    @classmethod
    def of(cls, money: Money, currency: str = "LKR") -> MoneyOut:
        return cls(cents=money.cents, currency=currency)


class StationOut(BaseModel):
    code: str
    name: str
    seq: int
    km: float

    @classmethod
    def of(cls, s: Station) -> StationOut:
        return cls(code=s.code, name=s.name, seq=s.seq, km=s.km)


class SeatOut(BaseModel):
    seat_id: str
    coach: str
    coach_type: CoachType
    travel_class: TravelClass
    number: int

    @classmethod
    def of(cls, s: Seat) -> SeatOut:
        return cls(
            seat_id=s.seat_id,
            coach=s.coach,
            coach_type=s.coach_type,
            travel_class=s.travel_class,
            number=s.number,
        )


class TripOut(BaseModel):
    trip_id: str
    route_code: str
    service_date: str
    stations: list[StationOut]
    seats: list[SeatOut]

    @classmethod
    def of(cls, t: Trip) -> TripOut:
        return cls(
            trip_id=t.trip_id,
            route_code=t.route_code,
            service_date=t.service_date,
            stations=[StationOut.of(s) for s in t.stations],
            seats=[SeatOut.of(s) for s in t.seats],
        )


class SeatAvailabilityOut(BaseModel):
    seat_id: str
    coach: str
    travel_class: TravelClass
    available: bool


class LegAvailabilityOut(BaseModel):
    trip_id: str
    origin_seq: int
    dest_seq: int
    free_count: int
    seats: list[SeatAvailabilityOut]

    @classmethod
    def of(cls, v: LegAvailability) -> LegAvailabilityOut:
        return cls(
            trip_id=v.trip_id,
            origin_seq=v.leg.origin_seq,
            dest_seq=v.leg.dest_seq,
            free_count=v.free_count,
            seats=[
                SeatAvailabilityOut(
                    seat_id=s.seat_id,
                    coach=s.coach,
                    travel_class=s.travel_class,
                    available=s.available,
                )
                for s in v.seats
            ],
        )


class BookingOut(BaseModel):
    booking_id: str
    reference: str
    trip_id: str
    seat_id: str
    origin_seq: int
    dest_seq: int
    passenger_id: str
    travel_class: TravelClass
    status: BookingStatus
    held_until: int
    created_at: int

    @classmethod
    def of(cls, h: Hold) -> BookingOut:
        return cls(
            booking_id=h.booking_id,
            reference=h.reference,
            trip_id=h.trip_id,
            seat_id=h.seat_id,
            origin_seq=h.leg.origin_seq,
            dest_seq=h.leg.dest_seq,
            passenger_id=h.passenger_id,
            travel_class=h.travel_class,
            status=h.status,
            held_until=h.held_until,
            created_at=h.created_at,
        )


class CancelOut(BaseModel):
    cancelled: BookingOut
    promoted: BookingOut | None = None

    @classmethod
    def of(cls, r: CancelResult) -> CancelOut:
        return cls(
            cancelled=BookingOut.of(r.cancelled),
            promoted=BookingOut.of(r.promoted) if r.promoted is not None else None,
        )


class WaitlistOut(BaseModel):
    waitlist_id: str
    trip_id: str
    origin_seq: int
    dest_seq: int
    passenger_id: str
    travel_class: TravelClass
    created_at: int

    @classmethod
    def of(cls, e: WaitlistEntry) -> WaitlistOut:
        return cls(
            waitlist_id=e.waitlist_id,
            trip_id=e.trip_id,
            origin_seq=e.leg.origin_seq,
            dest_seq=e.leg.dest_seq,
            passenger_id=e.passenger_id,
            travel_class=e.travel_class,
            created_at=e.created_at,
        )


class QuoteOut(BaseModel):
    trip_id: str
    origin_seq: int
    dest_seq: int
    travel_class: TravelClass
    fare: MoneyOut


class InvoiceOut(BaseModel):
    reference: str
    passenger_id: str
    trip_id: str
    service_date: str
    origin_seq: int
    dest_seq: int
    fare: MoneyOut
    status: BookingStatus
    issued_at: int
    seat_id: str | None = None
    standing_after: int | None = None
    standing_seat: int | None = None

    @classmethod
    def of(cls, inv: Invoice, currency: str = "LKR") -> InvoiceOut:
        return cls(
            reference=inv.reference,
            passenger_id=inv.passenger_id,
            trip_id=inv.trip_id,
            service_date=inv.service_date,
            origin_seq=inv.leg.origin_seq,
            dest_seq=inv.leg.dest_seq,
            fare=MoneyOut.of(inv.fare, currency),
            status=inv.status,
            issued_at=inv.issued_at,
            seat_id=inv.seat_id,
            standing_after=inv.standing_after,
            standing_seat=inv.standing_seat,
        )


class ImpactOut(BaseModel):
    trip_id: str
    active_legs: int
    seats_used: int
    seat_km_reclaimed: float

    @classmethod
    def of(cls, r: ImpactReport) -> ImpactOut:
        return cls(
            trip_id=r.trip_id,
            active_legs=r.active_legs,
            seats_used=r.seats_used,
            seat_km_reclaimed=r.seat_km_reclaimed,
        )


# ─── Request bodies ──────────────────────────────────────────────────────
class HoldRequest(BaseModel):
    trip_id: str
    seat_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    passenger_id: str = Field(min_length=1, max_length=64)
    travel_class: TravelClass
    reference: str | None = None


class UnreservedRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    passenger_id: str = Field(min_length=1, max_length=64)
    travel_class: TravelClass


class QuoteRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    travel_class: TravelClass


class WaitlistRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    passenger_id: str = Field(min_length=1, max_length=64)
    travel_class: TravelClass


class PromoteRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    seat_id: str
    travel_class: TravelClass


class SettleRequest(BaseModel):
    reference: str
