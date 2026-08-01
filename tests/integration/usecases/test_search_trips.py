import pytest
from tests.integration.usecases._helpers import build

from slr.usecases.search_trips import search_trips


@pytest.mark.integration
def test_search_finds_trips_on_the_route_and_date():
    deps = build()
    found = search_trips(deps, route_code="CMB-BAD", service_date="2026-08-01")
    assert [t.trip_id for t in found] == ["trip-1"]


@pytest.mark.integration
def test_search_is_empty_for_another_date():
    deps = build()
    assert search_trips(deps, route_code="CMB-BAD", service_date="2099-01-01") == []
