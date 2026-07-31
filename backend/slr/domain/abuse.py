"""Abuse heuristic (D9): a pure, bounded risk score behind the future AbuseScorer port.

Each signal is saturated at a config scale, then combined as a weighted average → a
value in [0,1]. Linear and monotonic on purpose: it's a placeholder for an ML model at
the same seam (swap the function, keep the port). No threshold decision lives here — the
use-case compares the score to a config cut-off.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

#: (weight, scale) per signal — `scale` is the value at which the signal saturates to 1.
Weight = tuple[float, float]


@dataclass(frozen=True, slots=True)
class AbuseFeatures:
    velocity: int          # bookings in the recent window
    passenger_fanout: int  # distinct passenger IDs from one actor
    seat_fanout: int       # distinct seats held at once
    cancel_ratio: float    # cancels / attempts, already in [0,1]


@dataclass(frozen=True, slots=True)
class AbuseWeights:
    velocity: Weight
    passenger_fanout: Weight
    seat_fanout: Weight
    cancel_ratio: Weight


DEFAULT_WEIGHTS = AbuseWeights(
    velocity=(1.0, 10),
    passenger_fanout=(1.5, 5),
    seat_fanout=(1.0, 6),
    cancel_ratio=(0.5, 1.0),
)


def _saturate(x: float) -> float:
    return min(1.0, max(0.0, x))


def abuse_score(features: AbuseFeatures, weights: AbuseWeights = DEFAULT_WEIGHTS) -> float:
    total_weight = 0.0
    weighted = 0.0
    for f in fields(AbuseFeatures):
        value = getattr(features, f.name)
        weight, scale = getattr(weights, f.name)
        total_weight += weight
        weighted += weight * _saturate(value / scale)
    if total_weight <= 0:
        raise ValueError("abuse weights must not all be zero")
    return weighted / total_weight
