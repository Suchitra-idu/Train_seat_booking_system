"""Notifier conformance. notify accepts a message and never raises."""

import pytest

from slr.adapters.memory_notifier import MemoryNotifier


@pytest.mark.integration
def test_notify_records_the_message():
    notifier = MemoryNotifier()
    notifier.notify("+94771234567", "HOLD_PLACED", {"reference": "SLR-000001"})
    assert notifier.sent == [
        ("+94771234567", "HOLD_PLACED", {"reference": "SLR-000001"})
    ]


@pytest.mark.integration
def test_notify_snapshots_the_detail_mapping():
    notifier = MemoryNotifier()
    detail = {"reference": "SLR-000001"}
    notifier.notify("x", "E", detail)
    detail["reference"] = "mutated"
    assert notifier.sent[0][2] == {"reference": "SLR-000001"}
