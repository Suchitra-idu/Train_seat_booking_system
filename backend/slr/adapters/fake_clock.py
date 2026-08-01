"""Advanceable fake clock for deterministic tests."""

from __future__ import annotations


class FakeClock:
    def __init__(self, start: int = 0) -> None:
        self._now = start

    def now(self) -> int:
        return self._now

    def advance(self, seconds: int) -> None:
        if seconds < 0:
            raise ValueError(f"cannot rewind the clock: {seconds}")
        self._now += seconds

    def set(self, epoch: int) -> None:
        self._now = epoch
