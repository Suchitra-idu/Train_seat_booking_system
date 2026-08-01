"""Availability-publisher conformance. publish delivers events. Observation differs by
adapter (the fake records, the real streams to subscribers), so each has its own read.
"""

import pytest

from slr.adapters.memory_publisher import MemoryPublisher
from slr.adapters.sse_publisher import SsePublisher
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.ports.availability import AvailabilityEvent


def _event(status):
    return AvailabilityEvent("trip-1", "seat-1", Leg(0, 2), status)


@pytest.fixture(params=["fake", "real"])
def publisher(request):
    return MemoryPublisher() if request.param == "fake" else SsePublisher()


@pytest.mark.integration
def test_publish_does_not_raise(publisher):
    publisher.publish(_event(BookingStatus.HELD))


@pytest.mark.integration
def test_memory_publisher_records_in_order():
    publisher = MemoryPublisher()
    first, second = _event(BookingStatus.HELD), _event(BookingStatus.CANCELLED)
    publisher.publish(first)
    publisher.publish(second)
    assert publisher.events == [first, second]


@pytest.mark.integration
def test_sse_publisher_delivers_to_subscribers_in_order():
    publisher = SsePublisher()
    stream = publisher.subscribe()
    first, second = _event(BookingStatus.HELD), _event(BookingStatus.CANCELLED)
    publisher.publish(first)
    publisher.publish(second)
    assert stream.get_nowait() == first
    assert stream.get_nowait() == second
