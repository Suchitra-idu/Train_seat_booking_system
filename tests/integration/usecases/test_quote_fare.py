import dataclasses

import pytest
from tests.integration.usecases._helpers import build

from slr.domain.fares import Money
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.hold_seat import hold_seat
from slr.usecases.quote_fare import quote_fare


class RecordingFare:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, float]] = []

    def price(self, *, distance_km: float, class_mult: float, occupancy: float) -> Money:
        self.calls.append((distance_km, class_mult, occupancy))
        return Money.rupees(1)


@pytest.mark.integration
def test_quote_passes_distance_class_and_occupancy_to_the_strategy():
    fare = RecordingFare()
    deps = dataclasses.replace(build(), fares=fare)
    quote_fare(deps, trip_id="trip-1", leg=Leg(0, 2), travel_class=TravelClass.FIRST)
    # [0,2) spans 20 km; FIRST multiplier is 2.0; no holds yet so occupancy is 0.
    assert fare.calls == [(20.0, 2.0, 0.0)]


@pytest.mark.integration
def test_occupancy_rises_as_seats_fill_over_the_leg():
    fare = RecordingFare()
    deps = dataclasses.replace(build(), fares=fare)  # 5 seats total
    hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        passenger_name="Ann Perera",
    )
    quote_fare(deps, trip_id="trip-1", leg=Leg(1, 2), travel_class=TravelClass.SECOND)
    assert fare.calls[-1][2] == pytest.approx(1 / 5)
