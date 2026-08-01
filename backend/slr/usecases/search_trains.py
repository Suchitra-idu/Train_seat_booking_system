"""Find the trains that serve a journey on a date (D22).

Search is the app's front door: two station codes and a date in, a list of departures out.
Only trips materialized for that date exist, so "runs on Tuesdays" is already answered by
the seeder; what is decided here is whether each train *calls* at both ends of the journey,
and what it costs and how long it takes over that particular leg.
"""

from __future__ import annotations

from dataclasses import dataclass

from slr.domain.errors import InvalidLeg, InvalidServiceDate
from slr.domain.fares import Money
from slr.domain.stations import Leg, Station
from slr.domain.timetable import (
    date_from_epoch,
    format_hhmm,
    leg_times,
    parse_date,
    serves,
    within_window,
)
from slr.domain.values import CLASS_ORDER, CoachType, TravelClass
from slr.ports.repository import Trip, UnitOfWork
from slr.usecases._deps import Deps
from slr.usecases._support import (
    BOOKING_WINDOW_DAYS,
    UTC_OFFSET_MINUTES,
    leg_distance_km,
    price_leg,
)


@dataclass(frozen=True, slots=True)
class ClassAvailability:
    travel_class: TravelClass
    free_seats: int
    fare: Money


@dataclass(frozen=True, slots=True)
class TrainOption:
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
    classes: tuple[ClassAvailability, ...]

    @property
    def free_seats(self) -> int:
        return sum(c.free_seats for c in self.classes)

    @property
    def from_fare(self) -> Money:
        return min((c.fare for c in self.classes), default=Money(0))


def search_trains(
    deps: Deps, *, origin_code: str, dest_code: str, service_date: str
) -> list[TrainOption]:
    parse_date(service_date)  # a malformed date is bad input, not an empty result
    if origin_code == dest_code:
        raise InvalidLeg("origin and destination are the same station")

    now = deps.clock.now()
    today = date_from_epoch(
        now, utc_offset_minutes=deps.config.get_int(UTC_OFFSET_MINUTES)
    )
    window = deps.config.get_int(BOOKING_WINDOW_DAYS)
    if not within_window(service_date, today=today, window_days=window):
        raise InvalidServiceDate(
            f"{service_date} is outside the booking window "
            f"({today} to {window} days ahead)"
        )

    with deps.uow as uow:
        uow.bookings.expire_due(now)
        options: list[TrainOption] = []
        for trip in uow.trips.find_by_date(service_date):
            option = _option(deps, uow, trip, origin_code, dest_code)
            if option is not None:
                options.append(option)
        uow.commit()
        return options


def _station(trip: Trip, code: str) -> Station | None:
    return next((s for s in trip.stations if s.code == code), None)


def _option(
    deps: Deps, uow: UnitOfWork, trip: Trip, origin_code: str, dest_code: str
) -> TrainOption | None:
    origin = _station(trip, origin_code)
    dest = _station(trip, dest_code)
    if origin is None or dest is None or origin.seq >= dest.seq:
        return None  # this train's route does not run this way round
    leg = Leg(origin.seq, dest.seq)
    if not serves(trip.stops, leg):
        return None  # it passes through without calling at both ends

    times = leg_times(trip.stops, leg)
    busy = {
        h.seat_id for h in uow.bookings.active_holds(trip.trip_id) if h.leg.overlaps(leg)
    }
    reservable = [s for s in trip.seats if s.coach_type is CoachType.RESERVED]

    present = {s.travel_class for s in reservable}
    classes = []
    for travel_class in (c for c in CLASS_ORDER if c in present):
        free = sum(
            1
            for s in reservable
            if s.travel_class is travel_class and s.seat_id not in busy
        )
        classes.append(
            ClassAvailability(
                travel_class=travel_class,
                free_seats=free,
                fare=price_leg(deps, uow, trip, leg, travel_class),
            )
        )

    return TrainOption(
        trip_id=trip.trip_id,
        train_no=trip.train_no,
        train_name=trip.train_name,
        route_code=trip.route_code,
        service_date=trip.service_date,
        origin_seq=origin.seq,
        dest_seq=dest.seq,
        depart=format_hhmm(times.depart_min),
        arrive=format_hhmm(times.arrive_min),
        duration_min=times.duration_min,
        distance_km=leg_distance_km(trip, leg),
        classes=tuple(classes),
    )
