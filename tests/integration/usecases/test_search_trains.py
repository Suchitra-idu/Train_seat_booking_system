import pytest
from tests.integration.usecases._helpers import DEFAULT_CONFIG, TODAY, build, make_trip

from slr.domain.errors import InvalidLeg, InvalidServiceDate
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.hold_seat import hold_seat
from slr.usecases.search_trains import search_trains

TOMORROW = "1970-01-02"


def _search(deps, origin="S0", dest="S3", date=TODAY):
    return search_trains(deps, origin_code=origin, dest_code=dest, service_date=date)


@pytest.mark.integration
def test_finds_the_trains_running_that_day():
    deps = build(
        trips=[
            make_trip("t1", service_date=TODAY, train_no="1005"),
            make_trip("t2", service_date=TOMORROW, train_no="1015"),
        ]
    )
    assert [o.train_no for o in _search(deps)] == ["1005"]
    assert [o.train_no for o in _search(deps, date=TOMORROW)] == ["1015"]


@pytest.mark.integration
def test_a_train_that_does_not_run_that_day_is_simply_absent():
    """The seeder only materializes the days a pattern runs (D22), so a weekday it skips
    has no trip at all rather than a trip flagged as not running."""
    deps = build(trips=[make_trip("t1", service_date=TOMORROW)])
    assert _search(deps, date=TODAY) == []


@pytest.mark.integration
def test_a_train_that_skips_the_origin_is_excluded():
    deps = build(
        trips=[
            make_trip("calls", service_date=TODAY, train_no="1005"),
            make_trip("skips", service_date=TODAY, train_no="1015", skip_stops=(1,)),
        ]
    )
    assert [o.train_no for o in _search(deps, origin="S1", dest="S3")] == ["1005"]


@pytest.mark.integration
def test_a_backwards_journey_returns_nothing():
    deps = build(trip=make_trip(service_date=TODAY))
    assert _search(deps, origin="S3", dest="S1") == []


@pytest.mark.integration
def test_the_same_station_twice_is_bad_input():
    deps = build(trip=make_trip(service_date=TODAY))
    with pytest.raises(InvalidLeg):
        _search(deps, origin="S1", dest="S1")


@pytest.mark.integration
def test_an_unknown_station_matches_no_train():
    deps = build(trip=make_trip(service_date=TODAY))
    assert _search(deps, origin="NOWHERE", dest="S3") == []


@pytest.mark.integration
@pytest.mark.parametrize("bad", ["", "not-a-date", "1970-13-01", "70-01-01"])
def test_a_malformed_date_fails_loud(bad):
    deps = build(trip=make_trip(service_date=TODAY))
    with pytest.raises(InvalidServiceDate):
        _search(deps, date=bad)


@pytest.mark.integration
def test_a_date_in_the_past_is_outside_the_window():
    deps = build(trip=make_trip(service_date=TODAY))
    with pytest.raises(InvalidServiceDate):
        _search(deps, date="1969-12-31")


@pytest.mark.integration
def test_a_date_beyond_the_booking_window_is_rejected():
    deps = build(
        trip=make_trip(service_date=TODAY),
        config={**DEFAULT_CONFIG, "booking_window_days": 2},
    )
    with pytest.raises(InvalidServiceDate):
        _search(deps, date="1970-01-03")


@pytest.mark.integration
def test_results_carry_times_duration_and_distance_for_that_leg():
    deps = build(trip=make_trip(service_date=TODAY))
    option = _search(deps, origin="S0", dest="S3")[0]
    assert option.depart == "08:05"  # station 0 departs at 485 minutes
    assert option.arrive == "11:00"  # station 3 arrives at 660
    assert option.duration_min == 175
    assert option.distance_km == 30.0


@pytest.mark.integration
def test_free_seats_drop_as_the_leg_fills():
    deps = build(trip=make_trip(reserved=3, service_date=TODAY))
    before = _search(deps)[0]
    assert before.free_seats == 3

    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(1, 2),
        passenger_id="p1",
        passenger_name="Ann",
    )
    after = _search(deps)[0]
    assert after.free_seats == 2  # [1,2) overlaps the searched [0,3)


@pytest.mark.integration
def test_a_seat_taken_on_a_different_leg_still_counts_as_free():
    """Segment resale (D2): a seat busy over [3,5) is available to a [0,3) passenger."""
    deps = build(trip=make_trip(reserved=1, service_date=TODAY))
    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(3, 5),
        passenger_id="p1",
        passenger_name="Ann",
    )
    assert _search(deps, origin="S0", dest="S3")[0].free_seats == 1


@pytest.mark.integration
def test_classes_are_listed_best_first_with_a_from_fare():
    deps = build(trip=make_trip(service_date=TODAY, travel_class=TravelClass.THIRD))
    option = _search(deps)[0]
    assert [c.travel_class for c in option.classes] == [TravelClass.THIRD]
    assert option.from_fare == option.classes[0].fare


@pytest.mark.integration
def test_unreserved_seats_are_not_counted_as_bookable():
    deps = build(trip=make_trip(reserved=2, unreserved=9, service_date=TODAY))
    assert _search(deps)[0].free_seats == 2
