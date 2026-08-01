"""Notifier port. Fire-and-forget user-facing messages."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class Notifier(Protocol):
    def notify(self, recipient: str, event: str, detail: Mapping[str, str]) -> None:
        ...
