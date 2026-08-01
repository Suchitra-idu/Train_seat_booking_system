"""Abuse-scorer conformance. The score is a probability. The fake is scriptable."""

import pytest

from slr.adapters.scripted_abuse import ScriptedAbuse
from slr.domain.abuse import AbuseFeatures

CLEAN = AbuseFeatures(velocity=0, passenger_fanout=0, seat_fanout=0, cancel_ratio=0.0)


@pytest.mark.integration
def test_score_is_a_probability():
    assert 0.0 <= ScriptedAbuse(default=0.3).score(CLEAN) <= 1.0


@pytest.mark.integration
def test_scripted_scores_are_returned_in_order_then_default():
    scorer = ScriptedAbuse(default=0.1, scores=[0.9, 0.5])
    assert scorer.score(CLEAN) == 0.9
    assert scorer.score(CLEAN) == 0.5
    assert scorer.score(CLEAN) == 0.1
