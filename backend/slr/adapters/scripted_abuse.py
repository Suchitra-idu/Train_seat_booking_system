"""Scripted abuse scorer. Returns queued scores, then a constant default."""

from __future__ import annotations

from collections.abc import Iterable

from slr.domain.abuse import AbuseFeatures


class ScriptedAbuse:
    def __init__(self, default: float = 0.0, scores: Iterable[float] = ()) -> None:
        self._default = default
        self._queue = list(scores)

    def score(self, features: AbuseFeatures) -> float:
        if self._queue:
            return self._queue.pop(0)
        return self._default
