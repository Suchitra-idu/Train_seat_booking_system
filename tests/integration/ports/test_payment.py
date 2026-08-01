"""Payment conformance. A successful charge reports ok; the fake can force a decline."""

import pytest

from slr.adapters.fake_payment import FakePayment
from slr.adapters.mock_payment import MockPayment
from slr.domain.fares import Money


@pytest.fixture(params=["fake", "real"])
def gateway(request):
    return FakePayment() if request.param == "fake" else MockPayment()


@pytest.mark.integration
def test_successful_charge_reports_ok(gateway):
    result = gateway.charge("SLR-000001", Money.rupees(1200))
    assert result.ok is True
    assert result.reference == "SLR-000001"


@pytest.mark.integration
def test_forced_decline_reports_not_ok_without_raising():
    result = FakePayment(decline=True).charge("SLR-000001", Money.rupees(1200))
    assert result.ok is False
    assert result.detail


@pytest.mark.integration
def test_decline_can_target_specific_references():
    gateway = FakePayment(decline_refs={"SLR-000002"})
    assert gateway.charge("SLR-000001", Money.rupees(10)).ok is True
    assert gateway.charge("SLR-000002", Money.rupees(10)).ok is False
