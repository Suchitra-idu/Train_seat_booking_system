"""Timetable rules (D22), pure: which train runs on which date, and when it calls.

A `ServicePattern` is config, a recurring template. A `Trip` is one dated instance of it,
materialized by the seeder (L4) because a `Trip` crosses a port and the domain may not
import ports. What lives here is everything that is a *rule* rather than an assembly:
whether a pattern runs on a date, whether its calling pattern serves a leg, and what the
leg's times are. Dates are ISO `YYYY-MM-DD` strings; times are minutes from midnight of
the service date, so an overnight arrival is simply > 1440.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from slr.domain.errors import InvalidLeg, InvalidServiceDate
from slr.domain.stations import Leg

MINUTES_PER_DAY = 1440

#: Monday-first, matching `date.weekday()`.
DAY_CODES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


@dataclass(frozen=True, slots=True)
class Stop:
    """One call on a trip. `arrive_min` is None at the origin, `depart_min` at the
    terminus, so a stop always has at least one time."""

    station_seq: int
    arrive_min: int | None
    depart_min: int | None

    def __post_init__(self) -> None:
        if self.station_seq < 0:
            raise InvalidServiceDate(f"negative station sequence: {self.station_seq}")
        if self.arrive_min is None and self.depart_min is None:
            raise InvalidServiceDate(f"stop {self.station_seq} has no times")


@dataclass(frozen=True, slots=True)
class LegTimes:
    depart_min: int
    arrive_min: int

    @property
    def duration_min(self) -> int:
        return self.arrive_min - self.depart_min


def parse_days(codes: Iterable[str]) -> frozenset[int]:
    """Day codes (`MON`…`SUN`) to `date.weekday()` numbers. Unknown code fails loud."""
    days = set()
    for code in codes:
        upper = code.strip().upper()
        if upper not in DAY_CODES:
            raise InvalidServiceDate(f"unknown day code: {code!r}")
        days.add(DAY_CODES.index(upper))
    if not days:
        raise InvalidServiceDate("a service pattern must run on at least one day")
    return frozenset(days)


def parse_hhmm(value: str) -> int:
    """`"08:30"` to minutes from midnight. A `+` prefix marks the next day: `"+02:15"`."""
    text = value.strip()
    day_offset = 0
    while text.startswith("+"):
        day_offset += 1
        text = text[1:]
    try:
        hours, minutes = (int(part) for part in text.split(":", 1))
    except ValueError:
        raise InvalidServiceDate(f"not a HH:MM time: {value!r}") from None
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise InvalidServiceDate(f"time out of range: {value!r}")
    return day_offset * MINUTES_PER_DAY + hours * 60 + minutes


def format_hhmm(minutes: int) -> str:
    """Minutes from midnight to `HH:MM`, wrapping past midnight."""
    within_day = minutes % MINUTES_PER_DAY
    return f"{within_day // 60:02d}:{within_day % 60:02d}"


def parse_date(service_date: str) -> date:
    try:
        return date.fromisoformat(service_date)
    except ValueError:
        raise InvalidServiceDate(f"not an ISO date: {service_date!r}") from None


def date_from_epoch(epoch: int, *, utc_offset_minutes: int = 0) -> str:
    """The local calendar date at an instant. The offset is config (D11), so "today"
    is Colombo's today rather than the server's."""
    moment = datetime.fromtimestamp(epoch, tz=UTC) + timedelta(minutes=utc_offset_minutes)
    return moment.date().isoformat()


def shift_date(service_date: str, days: int) -> str:
    return (parse_date(service_date) + timedelta(days=days)).isoformat()


def days_between(start_date: str, end_date: str) -> int:
    return (parse_date(end_date) - parse_date(start_date)).days


def runs_on(days_of_week: frozenset[int], service_date: str) -> bool:
    return parse_date(service_date).weekday() in days_of_week


def service_dates(
    days_of_week: frozenset[int], start_date: str, window_days: int
) -> list[str]:
    """Every date in `[start_date, start_date + window_days)` the pattern runs on."""
    if window_days < 0:
        raise InvalidServiceDate(f"negative booking window: {window_days}")
    first = parse_date(start_date)
    return [
        (first + timedelta(days=offset)).isoformat()
        for offset in range(window_days)
        if (first + timedelta(days=offset)).weekday() in days_of_week
    ]


def within_window(service_date: str, *, today: str, window_days: int) -> bool:
    """Bookable dates are today through the end of the booking window. The past is not
    bookable, and neither is a date beyond what the seeder has materialized."""
    offset = days_between(today, service_date)
    return 0 <= offset < window_days


def stop_at(stops: Sequence[Stop], station_seq: int) -> Stop | None:
    return next((s for s in stops if s.station_seq == station_seq), None)


def departure_min(stops: Sequence[Stop]) -> int:
    """When the train leaves its origin. The sort key for a day's departures."""
    times = [s.depart_min for s in stops if s.depart_min is not None]
    if not times:
        raise InvalidServiceDate("a trip must depart from somewhere")
    return min(times)


def serves(stops: Sequence[Stop], leg: Leg) -> bool:
    """True when the train calls at both ends of the leg, origin before destination.

    Station sequence is the line's order, so a trip that skips one end, or one asked for
    a backwards leg, does not serve it. `Leg` already rejects reversed intervals, so the
    ordering check here is about *this train's* calling pattern.
    """
    origin = stop_at(stops, leg.origin_seq)
    dest = stop_at(stops, leg.dest_seq)
    if origin is None or dest is None:
        return False
    return origin.depart_min is not None and dest.arrive_min is not None


def leg_times(stops: Sequence[Stop], leg: Leg) -> LegTimes:
    """Departure and arrival for one leg of this trip. Raises when the leg is not served."""
    origin = stop_at(stops, leg.origin_seq)
    dest = stop_at(stops, leg.dest_seq)
    if origin is None or dest is None or origin.depart_min is None or dest.arrive_min is None:
        raise InvalidLeg(f"this train does not serve [{leg.origin_seq}, {leg.dest_seq})")
    return LegTimes(origin.depart_min, dest.arrive_min)


def trip_id_for(pattern_code: str, service_date: str) -> str:
    """Deterministic, so re-seeding the same window is a no-op rather than a duplicate."""
    return f"{pattern_code}:{service_date}"
