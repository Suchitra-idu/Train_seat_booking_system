import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import InvalidLeg
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.join_waitlist import join_waitlist


@pytest.mark.integration
def test_join_records_a_waitlist_entry():
    deps = build()
    entry = join_waitlist(
        deps,
        trip_id="trip-1",
        leg=Leg(0, 3),
        passenger_id="p1",
        travel_class=TravelClass.SECOND,
    )
    assert entry.created_at == 1_000
    assert [e.waitlist_id for e in deps.uow.waitlist.for_trip("trip-1")] == [entry.waitlist_id]


@pytest.mark.integration
def test_join_rejects_a_leg_off_the_route():
    deps = build()
    with pytest.raises(InvalidLeg):
        join_waitlist(
            deps,
            trip_id="trip-1",
            leg=Leg(0, 99),
            passenger_id="p1",
            travel_class=TravelClass.SECOND,
        )
