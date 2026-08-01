"""Clock port. Wall time as epoch seconds, injected so the core stays clock-free (D12)."""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    def now(self) -> int:
        """Epoch seconds, non-decreasing across calls."""
        ...
