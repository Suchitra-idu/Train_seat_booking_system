"""Real clock. Wall time from the OS."""

from __future__ import annotations

import time


class SystemClock:
    def now(self) -> int:
        return int(time.time())
