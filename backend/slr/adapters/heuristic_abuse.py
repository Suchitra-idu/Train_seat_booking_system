"""Real abuse scorer (D9). The pure heuristic behind the ML-ready seam."""

from __future__ import annotations

from slr.domain.abuse import DEFAULT_WEIGHTS, AbuseFeatures, AbuseWeights, abuse_score


class HeuristicAbuse:
    def __init__(self, weights: AbuseWeights = DEFAULT_WEIGHTS) -> None:
        self._weights = weights

    def score(self, features: AbuseFeatures) -> float:
        return abuse_score(features, self._weights)
