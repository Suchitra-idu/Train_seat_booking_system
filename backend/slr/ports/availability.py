"""Availability-publisher port. Broadcast a seat/leg occupancy change to live clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from slr.domain.stations import Leg
from slr.domain.values import BookingStatus


@dataclass(frozen=True, slots=True)
class AvailabilityEvent:
    trip_id: str
    seat_id: str
    leg: Leg
    status: BookingStatus


class AvailabilityPublisher(Protocol):
    def publish(self, event: AvailabilityEvent) -> None:
        ...
