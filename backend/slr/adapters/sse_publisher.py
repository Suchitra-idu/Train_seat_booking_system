"""Real availability publisher (D7). A thread-safe in-process broker: each subscriber
gets a queue, and publish fans an event out to every current subscriber. The SSE HTTP
endpoint (P5) drains a subscriber queue into the response stream.
"""

from __future__ import annotations

import queue
import threading

from slr.ports.availability import AvailabilityEvent


class SsePublisher:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[AvailabilityEvent]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[AvailabilityEvent]:
        stream: queue.Queue[AvailabilityEvent] = queue.Queue()
        with self._lock:
            self._subscribers.append(stream)
        return stream

    def unsubscribe(self, stream: queue.Queue[AvailabilityEvent]) -> None:
        with self._lock:
            if stream in self._subscribers:
                self._subscribers.remove(stream)

    def publish(self, event: AvailabilityEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for stream in subscribers:
            stream.put(event)
