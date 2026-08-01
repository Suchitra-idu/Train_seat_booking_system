"""Clock conformance. now() returns non-decreasing epoch seconds, for fake and real."""

import pytest

from slr.adapters.fake_clock import FakeClock
from slr.adapters.system_clock import SystemClock


@pytest.fixture(params=["fake", "real"])
def clock(request):
    return FakeClock(start=1_000) if request.param == "fake" else SystemClock()


@pytest.mark.integration
def test_now_returns_int_epoch_seconds(clock):
    assert isinstance(clock.now(), int)


@pytest.mark.integration
def test_now_is_non_decreasing(clock):
    assert clock.now() <= clock.now()


@pytest.mark.integration
def test_fake_advances_and_refuses_to_rewind():
    clock = FakeClock(start=1_000)
    clock.advance(60)
    assert clock.now() == 1_060
    with pytest.raises(ValueError):
        clock.advance(-1)
