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
    assert values == ["HELD", "CONFIRMED", "CANCELLED", "EXPIRED", "STANDING", "PENDING"]
    assert len(set(values)) == len(values)


@pytest.mark.unit
def test_active_and_terminal_partition_the_lifecycle():
    # Active = occupies a *seat* (the overlap-invariant scope); terminal = frozen.
    assert {BookingStatus.HELD, BookingStatus.CONFIRMED} == ACTIVE_STATUSES
    assert {BookingStatus.CANCELLED, BookingStatus.EXPIRED} == TERMINAL_STATUSES
    assert not (ACTIVE_STATUSES & TERMINAL_STATUSES)


@pytest.mark.unit
def test_seatless_statuses_are_outside_the_invariant_scope():
    # PENDING (awaiting counter payment, D21) and STANDING (D20) are both live and hold
    # no seat, so neither is active and neither is terminal.
    for status in (BookingStatus.PENDING, BookingStatus.STANDING):
        assert status not in ACTIVE_STATUSES
        assert status not in TERMINAL_STATUSES


@pytest.mark.unit
def test_coach_and_travel_class_members():
    assert {c.value for c in CoachType} == {"RESERVED", "UNRESERVED"}
    assert {c.value for c in TravelClass} == {"FIRST", "SECOND", "THIRD"}
