"""Clock conformance. Runs against the fake now, the real system clock in P3."""

import pytest

from slr.adapters.fake_clock import FakeClock


@pytest.fixture
def clock():
    return FakeClock(start=1_000)


@pytest.mark.integration
def test_now_returns_int_epoch_seconds(clock):
    assert isinstance(clock.now(), int)


@pytest.mark.integration
def test_now_is_non_decreasing(clock):
    a = clock.now()
    b = clock.now()
    assert b >= a


@pytest.mark.integration
def test_fake_advances_and_refuses_to_rewind(clock):
    clock.advance(60)
    assert clock.now() == 1_060
    with pytest.raises(ValueError):
        clock.advance(-1)
