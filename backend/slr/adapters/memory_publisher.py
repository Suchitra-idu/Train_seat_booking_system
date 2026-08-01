"""In-memory availability publisher. Records events for assertions."""

from __future__ import annotations

from slr.ports.availability import AvailabilityEvent


class MemoryPublisher:
    def __init__(self) -> None:
        self.events: list[AvailabilityEvent] = []

    def publish(self, event: AvailabilityEvent) -> None:
        self.events.append(event)
