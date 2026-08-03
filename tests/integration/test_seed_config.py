"""P8 exit gate: coach/seat/station counts and the set of trains on a weekday come
straight from config/timetable.json, not from code. Editing the file, not this test,
is how a reviewer changes the fleet or the route.
"""

from __future__ import annotations

import json

import pytest

from slr.app.config import DEFAULT_TIMETABLE
from slr.app.timetable_config import build_coach, load_timetable
from slr.domain.timetable import runs_on

with open(DEFAULT_TIMETABLE, encoding="utf-8") as f:
    _RAW = json.load(f)


@pytest.mark.integration
def test_station_count_and_order_come_from_config():
    timetable = load_timetable(DEFAULT_TIMETABLE)
    assert [s.code for s in timetable.stations] == [s["code"] for s in _RAW["route"]["stations"]]


@pytest.mark.integration
def test_a_coach_layout_change_changes_the_seat_count():
    layout = _RAW["coach_layouts"]["second-reserved"]
    coach, seats = build_coach("B", layout)
    assert len(seats) == coach.rows * sum(int(p) for p in coach.columns.split("-"))

    bigger = {**layout, "rows": layout["rows"] + 1}
    _, more_seats = build_coach("B", bigger)
    assert len(more_seats) == len(seats) + sum(int(p) for p in layout["columns"].split("-"))


@pytest.mark.integration
def test_the_trains_on_a_weekday_come_from_each_pattern_days_of_week():
    timetable = load_timetable(DEFAULT_TIMETABLE)
    friday_trips = timetable.trips_for_window("2026-08-07", 1)  # a Friday
    monday_trips = timetable.trips_for_window("2026-08-03", 1)  # a Monday

    friday_trains = {t.train_no for t in friday_trips}
    monday_trains = {t.train_no for t in monday_trips}

    weekend_only = next(p for p in _RAW["service_patterns"] if len(p["days_of_week"]) < 7)
    assert weekend_only["train_no"] in friday_trains
    assert weekend_only["train_no"] not in monday_trains
    assert runs_on(frozenset({4}), "2026-08-07")  # sanity: 2026-08-07 is a Friday
