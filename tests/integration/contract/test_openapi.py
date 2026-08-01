"""The OpenAPI seam (D13): the committed contract must match the live app, and it must
carry every route the frontend generates a client against.
"""

import json
from pathlib import Path

import pytest
from scripts.emit_openapi import CONTRACT, build_schema

_EXPECTED = {
    ("get", "/trips"),
    ("get", "/trips/{trip_id}/availability"),
    ("get", "/trips/{trip_id}/impact"),
    ("get", "/trips/{trip_id}/stream"),
    ("post", "/quote"),
    ("post", "/bookings/hold"),
    ("post", "/unreserved"),
    ("post", "/bookings/{booking_id}/confirm"),
    ("post", "/bookings/{booking_id}/cancel"),
    ("get", "/bookings/{reference}"),
    ("post", "/waitlist"),
    ("post", "/waitlist/promote"),
    ("get", "/admin/bookings/{reference}"),
    ("post", "/admin/settle"),
}


@pytest.mark.contract
def test_committed_openapi_matches_the_live_app():
    committed = json.loads(Path(CONTRACT).read_text())
    assert committed == build_schema(), (
        "contract/openapi.json is stale — run `make emit-openapi` and commit the result"
    )


@pytest.mark.contract
def test_every_expected_route_is_in_the_contract():
    paths = build_schema()["paths"]
    live = {(method, path) for path, ops in paths.items() for method in ops}
    assert live >= _EXPECTED
