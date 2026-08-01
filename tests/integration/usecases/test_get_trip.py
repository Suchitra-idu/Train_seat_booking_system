import pytest
from tests.integration.usecases._helpers import build, make_trip

from slr.usecases.get_trip import get_trip


@pytest.mark.integration
def test_reads_the_trip_with_its_coaches_and_seats():
    deps = build(trip=make_trip(reserved=2, unreserved=1))
    trip = get_trip(deps, trip_id="trip-1")
    assert trip.train_no == "1005"
    assert [c.code for c in trip.coaches] == ["R1", "U1"]
    assert len(trip.seats) == 3
    assert trip.stops[0].depart_min == 485


@pytest.mark.integration
def test_an_unknown_trip_raises_keyerror_for_l4_to_map_to_404():
    deps = build()
    with pytest.raises(KeyError):
        get_trip(deps, trip_id="no-such-trip")
