import pytest

from slr.domain.values import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    BookingStatus,
    CoachType,
    TravelClass,
)


@pytest.mark.unit
def test_booking_statuses_are_distinct_strings():
    values = [s.value for s in BookingStatus]
    assert values == ["HELD", "CONFIRMED", "CANCELLED", "EXPIRED", "STANDING"]
    assert len(set(values)) == len(values)


@pytest.mark.unit
def test_active_and_terminal_partition_the_lifecycle():
    # Active = occupies a *seat* (the overlap-invariant scope); terminal = frozen.
    assert {BookingStatus.HELD, BookingStatus.CONFIRMED} == ACTIVE_STATUSES
    assert {BookingStatus.CANCELLED, BookingStatus.EXPIRED} == TERMINAL_STATUSES
    assert not (ACTIVE_STATUSES & TERMINAL_STATUSES)


@pytest.mark.unit
def test_standing_is_live_but_holds_no_seat():
    # A standing ticket (D20) is live but occupies coach standing capacity.
    # It sits outside the seat-overlap invariant's scope.
    assert BookingStatus.STANDING not in ACTIVE_STATUSES
    assert BookingStatus.STANDING not in TERMINAL_STATUSES


@pytest.mark.unit
def test_coach_and_travel_class_members():
    assert {c.value for c in CoachType} == {"RESERVED", "UNRESERVED"}
    assert {c.value for c in TravelClass} == {"FIRST", "SECOND", "THIRD"}
