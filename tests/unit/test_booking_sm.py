"""Booking lifecycle (D6): HELD → CONFIRMED, and HELD/CONFIRMED → CANCELLED/EXPIRED.
The machine is pure and clock-free — 'has the hold expired *in time*' is a use-case
question (needs the Clock port); here we only police which status changes are legal.
"""

import itertools

import pytest

from slr.domain.booking_sm import BookingEvent, apply, can_apply
from slr.domain.errors import IllegalTransition
from slr.domain.values import BookingStatus as S

LEGAL = {
    (S.HELD, BookingEvent.CONFIRM): S.CONFIRMED,
    (S.HELD, BookingEvent.CANCEL): S.CANCELLED,
    (S.HELD, BookingEvent.EXPIRE): S.EXPIRED,
    (S.CONFIRMED, BookingEvent.CANCEL): S.CANCELLED,
}


@pytest.mark.unit
@pytest.mark.parametrize("current,event,expected", [(k[0], k[1], v) for k, v in LEGAL.items()])
def test_legal_transitions(current, event, expected):
    assert apply(current, event) == expected
    assert can_apply(current, event)


@pytest.mark.unit
@pytest.mark.parametrize(
    "current,event",
    [(c, e) for c, e in itertools.product(S, BookingEvent) if (c, e) not in LEGAL],
)
def test_every_other_transition_is_illegal(current, event):
    assert not can_apply(current, event)
    with pytest.raises(IllegalTransition):
        apply(current, event)


@pytest.mark.unit
def test_cancelling_twice_is_rejected():
    cancelled = apply(S.HELD, BookingEvent.CANCEL)
    assert cancelled == S.CANCELLED
    with pytest.raises(IllegalTransition):
        apply(cancelled, BookingEvent.CANCEL)


@pytest.mark.unit
def test_cannot_confirm_after_expiry():
    expired = apply(S.HELD, BookingEvent.EXPIRE)
    with pytest.raises(IllegalTransition):
        apply(expired, BookingEvent.CONFIRM)


@pytest.mark.unit
def test_confirmed_booking_does_not_expire():
    with pytest.raises(IllegalTransition):
        apply(S.CONFIRMED, BookingEvent.EXPIRE)
