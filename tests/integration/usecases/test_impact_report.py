import pytest
from tests.integration.usecases._helpers import build

from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.hold_seat import hold_seat
from slr.usecases.impact_report import impact_report


def _hold(deps, seat_id, leg):
    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id=seat_id,
        leg=leg,
        passenger_id="p1",
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_impact_counts_reclaimed_seat_km_from_segment_resale():
    deps = build()
    _hold(deps, "R1", Leg(0, 2))
    _hold(deps, "R2", Leg(2, 4))
    report = impact_report(deps, trip_id="trip-1")
    assert report.active_legs == 2
    assert report.seats_used == 1  # adjacent legs pack onto one seat
    # route is 50 km; each 20 km leg leaves 30 km resellable that whole-journey would lock.
    assert report.seat_km_reclaimed == pytest.approx(60.0)


@pytest.mark.integration
def test_impact_is_zero_on_an_empty_trip():
    deps = build()
    report = impact_report(deps, trip_id="trip-1")
    assert report.active_legs == 0
    assert report.seat_km_reclaimed == pytest.approx(0.0)
