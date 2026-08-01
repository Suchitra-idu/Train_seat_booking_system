"""Timetable rules (D22): which dates a pattern runs, which legs it serves, and when.

Pure and clock-free, so "today" always arrives as a parameter. The property tests pin the
two rules a wrong answer would silently break: a pattern appears on exactly the weekdays it
declares, and a train that skips a station never serves a leg touching it.
"""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from slr.domain.errors import InvalidLeg, InvalidServiceDate
from slr.domain.stations import Leg
from slr.domain.timetable import (
    DAY_CODES,
    Stop,
    date_from_epoch,
    days_between,
    departure_min,
    format_hhmm,
    leg_times,
    parse_date,
    parse_days,
    parse_hhmm,
    runs_on,
    serves,
    service_dates,
    shift_date,
    stop_at,
    trip_id_for,
    within_window,
)

# A five-station train that skips station 2.
STOPS = (
    Stop(0, None, 500),
    Stop(1, 540, 545),
    Stop(3, 700, 705),
    Stop(4, 800, None),
)

DATES = st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1))


# ── day codes and dates ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_parse_days_maps_codes_to_weekday_numbers():
    assert parse_days(["MON", "sun"]) == frozenset({0, 6})


@pytest.mark.unit
@pytest.mark.parametrize("codes", [[], ["FUNDAY"], ["MON", "XXX"]])
def test_parse_days_rejects_nonsense(codes):
    with pytest.raises(InvalidServiceDate):
        parse_days(codes)


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["", "2026-13-01", "tomorrow", "01/08/2026", "2026-02-30"])
def test_parse_date_rejects_non_iso_dates(bad):
    with pytest.raises(InvalidServiceDate):
        parse_date(bad)


@pytest.mark.unit
def test_runs_on_matches_the_declared_weekdays():
    # 2026-08-03 is a Monday.
    assert runs_on(frozenset({0}), "2026-08-03")
    assert not runs_on(frozenset({0}), "2026-08-04")


@pytest.mark.unit
@given(day=st.integers(min_value=0, max_value=6), start=DATES)
def test_a_pattern_runs_on_exactly_the_weekdays_it_declares(day, start):
    dates = service_dates(frozenset({day}), start.isoformat(), 28)
    assert len(dates) == 4  # exactly four of that weekday in any 28-day span
    assert all(runs_on(frozenset({day}), d) for d in dates)


@pytest.mark.unit
def test_service_dates_is_empty_for_a_zero_window():
    assert service_dates(frozenset(range(7)), "2026-08-01", 0) == []


@pytest.mark.unit
def test_service_dates_rejects_a_negative_window():
    with pytest.raises(InvalidServiceDate):
        service_dates(frozenset({0}), "2026-08-01", -1)


@pytest.mark.unit
def test_within_window_excludes_the_past_and_the_far_future():
    assert within_window("2026-08-01", today="2026-08-01", window_days=30)
    assert within_window("2026-08-30", today="2026-08-01", window_days=30)
    assert not within_window("2026-07-31", today="2026-08-01", window_days=30)
    assert not within_window("2026-08-31", today="2026-08-01", window_days=30)


@pytest.mark.unit
def test_date_from_epoch_applies_the_local_offset():
    # 2026-08-01T20:00Z is already 2026-08-02 in Colombo (+05:30).
    epoch = 1_785_614_400
    assert date_from_epoch(epoch) == "2026-08-01"
    assert date_from_epoch(epoch, utc_offset_minutes=330) == "2026-08-02"


@pytest.mark.unit
def test_shift_and_difference_are_inverse():
    assert shift_date("2026-08-01", 10) == "2026-08-11"
    assert days_between("2026-08-01", "2026-08-11") == 10
    assert days_between("2026-08-11", "2026-08-01") == -10


# ── times ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "minutes"), [("00:00", 0), ("08:30", 510), ("23:59", 1439), ("+02:15", 1575)]
)
def test_parse_hhmm(text, minutes):
    assert parse_hhmm(text) == minutes


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["", "8:30pm", "24:00", "08:60", "-01:00", "half eight"])
def test_parse_hhmm_rejects_nonsense(bad):
    with pytest.raises(InvalidServiceDate):
        parse_hhmm(bad)


@pytest.mark.unit
@given(minutes=st.integers(min_value=0, max_value=1439))
def test_format_round_trips_within_a_day(minutes):
    assert parse_hhmm(format_hhmm(minutes)) == minutes


@pytest.mark.unit
def test_format_wraps_past_midnight():
    assert format_hhmm(1575) == "02:15"


@pytest.mark.unit
def test_a_stop_must_carry_at_least_one_time():
    with pytest.raises(InvalidServiceDate):
        Stop(2, None, None)


@pytest.mark.unit
def test_departure_is_the_origin_call():
    assert departure_min(STOPS) == 500


# ── serving a leg ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_stop_at_finds_only_stations_the_train_calls_at():
    assert stop_at(STOPS, 1).arrive_min == 540
    assert stop_at(STOPS, 2) is None


@pytest.mark.unit
def test_serves_a_leg_between_two_calls():
    assert serves(STOPS, Leg(0, 3))
    assert serves(STOPS, Leg(1, 4))


@pytest.mark.unit
@pytest.mark.parametrize("leg", [Leg(0, 2), Leg(2, 4), Leg(1, 5)])
def test_does_not_serve_a_leg_touching_a_skipped_or_absent_station(leg):
    assert not serves(STOPS, leg)


@pytest.mark.unit
def test_does_not_serve_a_leg_starting_at_the_terminus():
    # Station 4 is the last call: nothing departs from it.
    assert not serves((*STOPS, Stop(5, 900, None)), Leg(4, 5))


@pytest.mark.unit
def test_leg_times_are_the_calls_at_each_end():
    times = leg_times(STOPS, Leg(0, 3))
    assert (times.depart_min, times.arrive_min, times.duration_min) == (500, 700, 200)


@pytest.mark.unit
def test_leg_times_on_an_unserved_leg_is_an_error():
    with pytest.raises(InvalidLeg):
        leg_times(STOPS, Leg(0, 2))


@pytest.mark.unit
@given(origin=st.integers(0, 3), extra=st.integers(1, 3))
def test_duration_grows_with_the_leg(origin, extra):
    stops = tuple(Stop(i, None if i == 0 else i * 100, i * 100 + 5) for i in range(8))
    short = leg_times(stops, Leg(origin, origin + 1)).duration_min
    long = leg_times(stops, Leg(origin, origin + 1 + extra)).duration_min
    assert long > short


@pytest.mark.unit
def test_trip_ids_are_deterministic_per_pattern_and_date():
    assert trip_id_for("1005", "2026-08-01") == "1005:2026-08-01"


@pytest.mark.unit
def test_every_day_code_is_covered():
    assert len(DAY_CODES) == 7
    assert parse_days(DAY_CODES) == frozenset(range(7))
