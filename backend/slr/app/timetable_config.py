"""Load the timetable config and materialize it into dated trips (D22, D11).

Service patterns, coach layouts and the station list are data, not code: adding a train or
changing the days it runs is an edit to `config/timetable.json` plus a reseed. This module
is L4 because it reads a file and assembles `Trip` records, which cross a port; the rules it
applies (which dates a pattern runs, seat geometry) are pure and live in `domain/timetable`
and here as plain layout arithmetic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from slr.domain.stations import Station
from slr.domain.timetable import Stop, parse_days, parse_hhmm, service_dates, trip_id_for
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Coach, Seat, Trip

#: A..F, left block then right block. Enough for any layout the config can express.
COLUMN_LETTERS = "ABCDEFGH"


@dataclass(frozen=True, slots=True)
class ServicePattern:
    code: str
    train_no: str
    name: str
    days_of_week: frozenset[int]
    stops: tuple[Stop, ...]
    coaches: tuple[Coach, ...]
    seats: tuple[Seat, ...]


@dataclass(frozen=True, slots=True)
class Timetable:
    route_code: str
    route_name: str
    stations: tuple[Station, ...]
    patterns: tuple[ServicePattern, ...]

    def trips_for_window(self, start_date: str, window_days: int) -> list[Trip]:
        """Every dated trip in `[start_date, start_date + window_days)`."""
        return [
            self.materialize(pattern, date)
            for pattern in self.patterns
            for date in service_dates(pattern.days_of_week, start_date, window_days)
        ]

    def materialize(self, pattern: ServicePattern, service_date: str) -> Trip:
        return Trip(
            trip_id=trip_id_for(pattern.code, service_date),
            route_code=self.route_code,
            service_date=service_date,
            train_no=pattern.train_no,
            train_name=pattern.name,
            stations=self.stations,
            stops=pattern.stops,
            coaches=pattern.coaches,
            seats=pattern.seats,
        )


def column_labels(columns: str) -> list[str]:
    """"3-3" to ["A","B","C","D","E","F"]. The dash is the aisle; the map draws it."""
    per_block = [int(part) for part in columns.split("-")]
    total = sum(per_block)
    if total > len(COLUMN_LETTERS):
        raise ValueError(f"coach layout {columns!r} is wider than {len(COLUMN_LETTERS)} seats")
    return list(COLUMN_LETTERS[:total])


def build_coach(code: str, layout: dict) -> tuple[Coach, list[Seat]]:
    """One coach and its seats from a layout. Seat ids are `{coach}{row}{column}`, so a
    seat's id, its label on the map, and its physical place all agree."""
    coach = Coach(
        code=code,
        coach_type=CoachType(layout["coach_type"]),
        travel_class=TravelClass(layout["travel_class"]),
        rows=int(layout["rows"]),
        columns=str(layout["columns"]),
        exit_rows=tuple(int(r) for r in layout.get("exit_rows", ())),
    )
    letters = column_labels(coach.columns)
    seats = [
        Seat(
            seat_id=f"{code}{row}{letter}",
            coach=code,
            coach_type=coach.coach_type,
            travel_class=coach.travel_class,
            number=(row - 1) * len(letters) + index + 1,
            row=row,
            column=letter,
        )
        for row in range(1, coach.rows + 1)
        for index, letter in enumerate(letters)
    ]
    return coach, seats


def _stops(raw_stops: list[dict], seq_by_code: dict[str, int]) -> tuple[Stop, ...]:
    stops = []
    for entry in raw_stops:
        code = entry["station"]
        if code not in seq_by_code:
            raise ValueError(f"stop at unknown station {code!r}")
        arrive = entry.get("arrive")
        depart = entry.get("depart")
        stops.append(
            Stop(
                station_seq=seq_by_code[code],
                arrive_min=parse_hhmm(arrive) if arrive else None,
                depart_min=parse_hhmm(depart) if depart else None,
            )
        )
    return tuple(sorted(stops, key=lambda s: s.station_seq))


def load_timetable(path: str | Path) -> Timetable:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    route = raw["route"]
    stations = tuple(
        Station(code=s["code"], name=s["name"], seq=seq, km=float(s["km"]))
        for seq, s in enumerate(route["stations"])
    )
    seq_by_code = {s.code: s.seq for s in stations}
    layouts = raw["coach_layouts"]

    patterns = []
    for entry in raw["service_patterns"]:
        coaches: list[Coach] = []
        seats: list[Seat] = []
        for spec in entry["coaches"]:
            coach, coach_seats = build_coach(spec["code"], layouts[spec["layout"]])
            coaches.append(coach)
            seats.extend(coach_seats)
        patterns.append(
            ServicePattern(
                code=entry["code"],
                train_no=entry["train_no"],
                name=entry["name"],
                days_of_week=parse_days(entry["days_of_week"]),
                stops=_stops(entry["stops"], seq_by_code),
                coaches=tuple(coaches),
                seats=tuple(seats),
            )
        )

    return Timetable(
        route_code=route["code"],
        route_name=route["name"],
        stations=stations,
        patterns=tuple(patterns),
    )
