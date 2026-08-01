"""In-memory notifier. Records messages for assertions."""

from __future__ import annotations

from collections.abc import Mapping


class MemoryNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, dict[str, str]]] = []

    def notify(self, recipient: str, event: str, detail: Mapping[str, str]) -> None:
        self.sent.append((recipient, event, dict(detail)))
