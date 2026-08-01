"""The API contract, as Pydantic models (D13). FastAPI turns these into the OpenAPI
schema the frontend generates its client from, and the same models validate responses at
runtime on both sides of the seam. `of` builders map domain/use-case results in.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from slr.domain.fares import Money
from slr.domain.stations import Station
from slr.domain.timetable import Stop, format_hhmm
from slr.domain.values import BookingStatus, CoachType, TravelClass
from slr.ports.repository import Coach, Hold, Seat, Trip
from slr.usecases._receipt import Receipt
from slr.usecases.impact_report import ImpactReport
from slr.usecases.leg_availability import LegAvailability
from slr.usecases.search_trains import TrainOption
from slr.usecases.verify_ticket import Verdict, Verification


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


class StopOut(BaseModel):
    """A call on this trip. Times are HH:MM local; `null` marks the origin's arrival and
    the terminus' departure."""

    station_seq: int
    arrive: str | None
    depart: str | None

    @classmethod
    def of(cls, s: Stop) -> StopOut:
        return cls(
            station_seq=s.station_seq,
            arrive=format_hhmm(s.arrive_min) if s.arrive_min is not None else None,
            depart=format_hhmm(s.depart_min) if s.depart_min is not None else None,
        )


class CoachOut(BaseModel):
    """Seating geometry for the seat map (D25): `columns` is the per-side seat pattern
    ("3-3"), `exit_rows` the rows the map breaks after."""

    code: str
    coach_type: CoachType
    travel_class: TravelClass
    rows: int
    columns: str
    exit_rows: list[int]

    @classmethod
    def of(cls, c: Coach) -> CoachOut:
        return cls(
            code=c.code,
            coach_type=c.coach_type,
            travel_class=c.travel_class,
            rows=c.rows,
            columns=c.columns,
            exit_rows=list(c.exit_rows),
        )


class SeatOut(BaseModel):
    seat_id: str
    coach: str
    coach_type: CoachType
    travel_class: TravelClass
    number: int
    row: int
    column: str

    @classmethod
    def of(cls, s: Seat) -> SeatOut:
        return cls(
            seat_id=s.seat_id,
            coach=s.coach,
            coach_type=s.coach_type,
            travel_class=s.travel_class,
            number=s.number,
            row=s.row,
            column=s.column,
        )


class TripOut(BaseModel):
    trip_id: str
    route_code: str
    service_date: str
    train_no: str
    train_name: str
    stations: list[StationOut]
    stops: list[StopOut]
    coaches: list[CoachOut]
    seats: list[SeatOut]

    @classmethod
    def of(cls, t: Trip) -> TripOut:
        return cls(
            trip_id=t.trip_id,
            route_code=t.route_code,
            service_date=t.service_date,
            train_no=t.train_no,
            train_name=t.train_name,
            stations=[StationOut.of(s) for s in t.stations],
            stops=[StopOut.of(s) for s in t.stops],
            coaches=[CoachOut.of(c) for c in t.coaches],
            seats=[SeatOut.of(s) for s in t.seats],
        )


class ClassAvailabilityOut(BaseModel):
    travel_class: TravelClass
    free_seats: int
    fare: MoneyOut


class TrainOptionOut(BaseModel):
    """One search result: a train that serves the journey, with its times over *that* leg."""

    trip_id: str
    train_no: str
    train_name: str
    route_code: str
    service_date: str
    origin_seq: int
    dest_seq: int
    depart: str
    arrive: str
    duration_min: int
    distance_km: float
    free_seats: int
    from_fare: MoneyOut
    classes: list[ClassAvailabilityOut]

    @classmethod
    def of(cls, o: TrainOption, currency: str = "LKR") -> TrainOptionOut:
        return cls(
            trip_id=o.trip_id,
            train_no=o.train_no,
            train_name=o.train_name,
            route_code=o.route_code,
            service_date=o.service_date,
            origin_seq=o.origin_seq,
            dest_seq=o.dest_seq,
            depart=o.depart,
            arrive=o.arrive,
            duration_min=o.duration_min,
            distance_km=o.distance_km,
            free_seats=o.free_seats,
            from_fare=MoneyOut.of(o.from_fare, currency),
            classes=[
                ClassAvailabilityOut(
                    travel_class=c.travel_class,
                    free_seats=c.free_seats,
                    fare=MoneyOut.of(c.fare, currency),
                )
                for c in o.classes
            ],
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
    """A booking in flight: what the hold and cancel routes return. A *paid* booking is a
    receipt (ReceiptOut), which is what the passenger keeps."""

    booking_id: str
    reference: str
    trip_id: str
    seat_id: str
    origin_seq: int
    dest_seq: int
    passenger_id: str
    passenger_name: str
    travel_class: TravelClass
    status: BookingStatus
    fare: MoneyOut
    held_until: int
    created_at: int

    @classmethod
    def of(cls, h: Hold, currency: str = "LKR") -> BookingOut:
        return cls(
            booking_id=h.booking_id,
            reference=h.reference,
            trip_id=h.trip_id,
            seat_id=h.seat_id,
            origin_seq=h.leg.origin_seq,
            dest_seq=h.leg.dest_seq,
            passenger_id=h.passenger_id,
            passenger_name=h.passenger_name,
            travel_class=h.travel_class,
            status=h.status,
            fare=MoneyOut.of(Money(h.fare_cents), currency),
            held_until=h.held_until,
            created_at=h.created_at,
        )


class StandingOut(BaseModel):
    """D20's advice on a standing ticket: a seat frees at this station."""

    after_seq: int
    after_station: str
    seat_label: str


class ReceiptOut(BaseModel):
    """The ticket (D24). One shape whether it was bought in the app or at the counter;
    `qr_payload` is the reference the admin app verifies online."""

    reference: str
    qr_payload: str
    booking_id: str
    passenger_id: str
    passenger_name: str
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
    fare: MoneyOut
    status: BookingStatus
    issued_at: int
    coach: str | None = None
    seat_label: str | None = None
    standing: StandingOut | None = None

    @classmethod
    def of(cls, r: Receipt, currency: str = "LKR") -> ReceiptOut:
        return cls(
            reference=r.reference,
            qr_payload=r.qr_payload,
            booking_id=r.booking_id,
            passenger_id=r.passenger_id,
            passenger_name=r.passenger_name,
            trip_id=r.trip_id,
            route_code=r.route_code,
            train_no=r.train_no,
            train_name=r.train_name,
            service_date=r.service_date,
            origin_code=r.origin_code,
            origin_name=r.origin_name,
            origin_seq=r.origin_seq,
            dest_code=r.dest_code,
            dest_name=r.dest_name,
            dest_seq=r.dest_seq,
            depart=r.depart,
            arrive=r.arrive,
            duration_min=r.duration_min,
            travel_class=r.travel_class,
            fare=MoneyOut.of(r.fare, currency),
            status=r.status,
            issued_at=r.issued_at,
            coach=r.coach,
            seat_label=r.seat_label,
            standing=(
                StandingOut(
                    after_seq=r.standing.after_seq,
                    after_station=r.standing.after_station,
                    seat_label=r.standing.seat_label,
                )
                if r.standing is not None
                else None
            ),
        )


class VerifyOut(BaseModel):
    verdict: Verdict
    valid: bool
    ticket: ReceiptOut

    @classmethod
    def of(cls, v: Verification, currency: str = "LKR") -> VerifyOut:
        return cls(
            verdict=v.verdict,
            valid=v.valid,
            ticket=ReceiptOut.of(v.receipt, currency),
        )


class QuoteOut(BaseModel):
    trip_id: str
    origin_seq: int
    dest_seq: int
    travel_class: TravelClass
    fare: MoneyOut


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
NAME = Field(min_length=1, max_length=120)
NIC = Field(min_length=1, max_length=64)


class HoldRequest(BaseModel):
    """No travel class: the seat already knows its own, so it cannot be misdeclared."""

    trip_id: str
    seat_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    passenger_id: str = NIC
    passenger_name: str = NAME
    reference: str | None = None


class QuoteRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    travel_class: TravelClass


class SellUnreservedRequest(BaseModel):
    trip_id: str
    origin_seq: int = Field(ge=0)
    dest_seq: int = Field(ge=0)
    passenger_id: str = NIC
    passenger_name: str = NAME
    travel_class: TravelClass
