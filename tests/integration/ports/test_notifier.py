"""Notifier conformance. notify accepts a message and never raises, for fake and real."""

import pytest

from slr.adapters.log_notifier import LogNotifier
from slr.adapters.memory_notifier import MemoryNotifier


@pytest.fixture(params=["fake", "real"])
def notifier(request):
    return MemoryNotifier() if request.param == "fake" else LogNotifier()


@pytest.mark.integration
def test_notify_does_not_raise(notifier):
    notifier.notify("+94771234567", "HOLD_PLACED", {"reference": "SLR-000001"})


@pytest.mark.integration
def test_memory_notifier_records_and_snapshots_detail():
    notifier = MemoryNotifier()
    detail = {"reference": "SLR-000001"}
    notifier.notify("+94771234567", "HOLD_PLACED", detail)
    detail["reference"] = "mutated"
    assert notifier.sent == [("+94771234567", "HOLD_PLACED", {"reference": "SLR-000001"})]
