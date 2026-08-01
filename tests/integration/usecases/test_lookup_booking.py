import pytest
from tests.integration.usecases._helpers import build

from slr.domain.errors import BookingNotFound
from slr.domain.stations import Leg
from slr.domain.values import TravelClass
from slr.usecases.hold_seat import hold_seat
from slr.usecases.lookup_booking import lookup_booking


def _hold(deps):
    return hold_seat(
        deps,
        trip_id="trip-1",
        seat_id="R1",
        leg=Leg(0, 3),
        passenger_id="p1",
        travel_class=TravelClass.SECOND,
    )


@pytest.mark.integration
def test_lookup_by_reference_and_by_id():
    deps = build()
    hold = _hold(deps)
    assert lookup_booking(deps, reference=hold.reference).booking_id == hold.booking_id
    assert lookup_booking(deps, booking_id=hold.booking_id).reference == hold.reference


@pytest.mark.integration
def test_missing_reference_and_id_raise_not_found():
    deps = build()
    with pytest.raises(BookingNotFound):
        lookup_booking(deps, reference="SLR-nope")
    with pytest.raises(BookingNotFound):
        lookup_booking(deps, booking_id="nope")


@pytest.mark.integration
def test_lookup_without_a_key_is_a_programming_error():
    deps = build()
    with pytest.raises(ValueError):
        lookup_booking(deps)
