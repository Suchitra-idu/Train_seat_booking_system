"""Abuse-scorer conformance. The score is a probability, for fake and real."""

import pytest

from slr.adapters.heuristic_abuse import HeuristicAbuse
from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.domain.abuse import AbuseFeatures

CLEAN = AbuseFeatures(velocity=0, passenger_fanout=0, seat_fanout=0, cancel_ratio=0.0)
BUSY = AbuseFeatures(velocity=8, passenger_fanout=8, seat_fanout=8, cancel_ratio=0.9)


@pytest.fixture(params=["fake", "real"])
def scorer(request):
    return ScriptedAbuse(default=0.3) if request.param == "fake" else HeuristicAbuse()


@pytest.mark.integration
@pytest.mark.parametrize("features", [CLEAN, BUSY])
def test_score_is_a_probability(scorer, features):
    assert 0.0 <= scorer.score(features) <= 1.0


@pytest.mark.integration
def test_scripted_scores_are_returned_in_order_then_default():
    scorer = ScriptedAbuse(default=0.1, scores=[0.9, 0.5])
    assert scorer.score(CLEAN) == 0.9
    assert scorer.score(CLEAN) == 0.5
    assert scorer.score(CLEAN) == 0.1


@pytest.mark.integration
def test_heuristic_scores_a_clean_actor_at_zero():
    assert HeuristicAbuse().score(CLEAN) == 0.0
