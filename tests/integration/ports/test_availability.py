"""Availability-publisher conformance. Published events are retrievable in order."""

import pytest

from slr.adapters.memory_publisher import MemoryPublisher
from slr.domain.stations import Leg
from slr.domain.values import BookingStatus
from slr.ports.availability import AvailabilityEvent


@pytest.mark.integration
def test_publish_records_events_in_order():
    pub = MemoryPublisher()
    e1 = AvailabilityEvent("trip-1", "seat-1", Leg(0, 2), BookingStatus.HELD)
    e2 = AvailabilityEvent("trip-1", "seat-1", Leg(0, 2), BookingStatus.CANCELLED)
    pub.publish(e1)
    pub.publish(e2)
    assert pub.events == [e1, e2]
