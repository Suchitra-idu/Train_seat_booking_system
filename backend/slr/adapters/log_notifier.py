"""Real notifier. Writes each message to the log."""

from __future__ import annotations

import logging
from collections.abc import Mapping

_log = logging.getLogger("slr.notifier")


class LogNotifier:
    def notify(self, recipient: str, event: str, detail: Mapping[str, str]) -> None:
        _log.info("notify recipient=%s event=%s detail=%s", recipient, event, dict(detail))
