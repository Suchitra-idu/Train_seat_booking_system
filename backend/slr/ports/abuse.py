"""Abuse-scorer port. A risk score in [0,1] (D9). Thresholding lives in the use-case."""

from __future__ import annotations

from typing import Protocol

from slr.domain.abuse import AbuseFeatures


class AbuseScorer(Protocol):
    def score(self, features: AbuseFeatures) -> float:
        ...
