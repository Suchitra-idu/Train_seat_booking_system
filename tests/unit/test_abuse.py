"""Abuse heuristic (D9), a pure score in [0,1] behind what will become the
AbuseScorer port (heuristic now, ML-ready later). Weights/scales are config, so the
tests assert *shape*, bounded, monotonic in every risk signal, zero on a clean actor,
plus one hand-computed oracle. No thresholding here; the use-case compares to a config.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from slr.domain.abuse import DEFAULT_WEIGHTS, AbuseFeatures, AbuseWeights, abuse_score

CLEAN = AbuseFeatures(velocity=0, passenger_fanout=0, seat_fanout=0, cancel_ratio=0.0)


def features():
    return st.builds(
        AbuseFeatures,
        velocity=st.integers(min_value=0, max_value=100),
        passenger_fanout=st.integers(min_value=0, max_value=100),
        seat_fanout=st.integers(min_value=0, max_value=100),
        cancel_ratio=st.floats(min_value=0, max_value=1),
    )


@pytest.mark.unit
def test_clean_actor_scores_zero():
    assert abuse_score(CLEAN) == 0.0


@pytest.mark.unit
@given(features())
def test_score_is_always_a_probability(f):
    assert 0.0 <= abuse_score(f) <= 1.0


@pytest.mark.unit
def test_saturated_actor_scores_one():
    hot = AbuseFeatures(
        velocity=10_000, passenger_fanout=10_000, seat_fanout=10_000, cancel_ratio=1.0
    )
    assert abuse_score(hot) == pytest.approx(1.0)


@pytest.mark.unit
@given(features(), st.integers(min_value=1, max_value=50))
def test_more_velocity_never_lowers_the_score(f, bump):
    hotter = AbuseFeatures(f.velocity + bump, f.passenger_fanout, f.seat_fanout, f.cancel_ratio)
    assert abuse_score(hotter) >= abuse_score(f)


@pytest.mark.unit
@given(features(), st.integers(min_value=1, max_value=50))
def test_more_passenger_fanout_never_lowers_the_score(f, bump):
    hotter = AbuseFeatures(f.velocity, f.passenger_fanout + bump, f.seat_fanout, f.cancel_ratio)
    assert abuse_score(hotter) >= abuse_score(f)


@pytest.mark.unit
def test_a_zero_weighted_signal_is_ignored():
    # weight passenger_fanout at 0 → varying it must not move the score
    weights = AbuseWeights(
        velocity=(1.0, 10),
        passenger_fanout=(0.0, 10),
        seat_fanout=(1.0, 10),
        cancel_ratio=(1.0, 1.0),
    )
    lo = AbuseFeatures(5, 0, 5, 0.5)
    hi = AbuseFeatures(5, 99, 5, 0.5)
    assert abuse_score(lo, weights) == abuse_score(hi, weights)


@pytest.mark.unit
def test_oracle_hand_computed_weighted_average():
    # equal weights, scale 10; velocity 5 -> 0.5, fanout 10 -> 1.0 (saturated),
    # seat 0 -> 0.0, cancel_ratio 0.0 -> 0.0. mean = (0.5+1.0+0+0)/4 = 0.375
    weights = AbuseWeights(
        velocity=(1.0, 10),
        passenger_fanout=(1.0, 10),
        seat_fanout=(1.0, 10),
        cancel_ratio=(1.0, 1.0),
    )
    f = AbuseFeatures(velocity=5, passenger_fanout=10, seat_fanout=0, cancel_ratio=0.0)
    assert abuse_score(f, weights) == pytest.approx(0.375)


@pytest.mark.unit
def test_all_zero_weights_is_rejected():
    all_zero = AbuseWeights(
        velocity=(0.0, 10),
        passenger_fanout=(0.0, 10),
        seat_fanout=(0.0, 10),
        cancel_ratio=(0.0, 1.0),
    )
    with pytest.raises(ValueError):
        abuse_score(CLEAN, all_zero)


@pytest.mark.unit
def test_default_weights_exist_and_are_usable():
    assert isinstance(DEFAULT_WEIGHTS, AbuseWeights)
    assert 0.0 <= abuse_score(AbuseFeatures(3, 3, 3, 0.2), DEFAULT_WEIGHTS) <= 1.0
