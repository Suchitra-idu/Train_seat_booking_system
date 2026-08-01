"""Every route exercised on the fake Container: each response is re-parsed through its
contract model (runtime schema validation, D13) and the domain-error -> HTTP mapping is
pinned. This is the whole HTTP surface, proven without infrastructure.
"""

import pytest
from fastapi.testclient import TestClient
from tests.integration.contract.conftest import COUNTER_KEY, _settings
from tests.integration.usecases._helpers import make_trip

from slr.app.main import create_app
from slr.app.schemas import (
    BookingOut,
    CancelOut,
    InvoiceOut,
    LegAvailabilityOut,
    QuoteOut,
    TripOut,
    WaitlistOut,
)
from slr.app.wiring import wire_fake


def _client(**kw) -> TestClient:
    return TestClient(create_app(container=wire_fake((make_trip(),), **kw), settings=_settings()))


def _hold(client, seat_id="R1", origin=0, dest=3, passenger="p1", **extra):
    body = {
        "trip_id": "trip-1",
        "seat_id": seat_id,
        "origin_seq": origin,
        "dest_seq": dest,
        "passenger_id": passenger,
        "travel_class": "SECOND",
        **extra,
    }
    return client.post("/bookings/hold", json=body)


@pytest.mark.contract
def test_health_is_ok(client):
    assert client.get("/").json()["status"] == "ok"


@pytest.mark.contract
def test_search_trips_conforms(client):
    r = client.get("/trips", params={"route_code": "CMB-BAD", "service_date": "2026-08-01"})
    assert r.status_code == 200
    trips = [TripOut.model_validate(t) for t in r.json()]
    assert trips[0].trip_id == "trip-1"


@pytest.mark.contract
def test_availability_conforms(client):
    r = client.get("/trips/trip-1/availability", params={"origin_seq": 0, "dest_seq": 3})
    assert r.status_code == 200
    view = LegAvailabilityOut.model_validate(r.json())
    assert view.free_count == len(view.seats)


@pytest.mark.contract
def test_quote_conforms(client):
    r = client.post(
        "/quote",
        json={"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 3, "travel_class": "SECOND"},
    )
    assert r.status_code == 200
    assert QuoteOut.model_validate(r.json()).fare.cents > 0


@pytest.mark.contract
def test_hold_confirm_cancel_lifecycle(client):
    held = _hold(client)
    assert held.status_code == 201
    booking = BookingOut.model_validate(held.json())
    assert booking.status == "HELD"

    confirmed = client.post(f"/bookings/{booking.booking_id}/confirm")
    assert confirmed.status_code == 200
    assert BookingOut.model_validate(confirmed.json()).status == "CONFIRMED"

    cancelled = client.post(f"/bookings/{booking.booking_id}/cancel")
    assert cancelled.status_code == 200
    result = CancelOut.model_validate(cancelled.json())
    assert result.cancelled.status == "CANCELLED"


@pytest.mark.contract
def test_lookup_by_reference(client):
    ref = BookingOut.model_validate(_hold(client).json()).reference
    r = client.get(f"/bookings/{ref}")
    assert r.status_code == 200
    assert BookingOut.model_validate(r.json()).reference == ref


@pytest.mark.contract
def test_overlapping_hold_is_409(client):
    _hold(client, origin=0, dest=3, passenger="p1")
    clash = _hold(client, origin=1, dest=2, passenger="p2")
    assert clash.status_code == 409
    assert clash.json()["error"] == "OverlapError"


@pytest.mark.contract
def test_non_reserved_seat_is_422(client):
    r = _hold(client, seat_id="U1")
    assert r.status_code == 422
    assert r.json()["error"] == "SeatNotBookable"


@pytest.mark.contract
def test_reversed_leg_is_422(client):
    r = _hold(client, origin=3, dest=1)
    assert r.status_code == 422
    assert r.json()["error"] == "InvalidLeg"


@pytest.mark.contract
def test_lookup_missing_is_404(client):
    r = client.get("/bookings/SLR-does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"] == "BookingNotFound"


@pytest.mark.contract
def test_velocity_limit_is_429():
    client = _client()  # default max_bookings_per_window is 3
    for seat in ("R1", "R2", "R3"):
        assert _hold(client, seat_id=seat, origin=0, dest=1, passenger="p1").status_code == 201
    fourth = _hold(client, seat_id="R1", origin=1, dest=2, passenger="p1")
    assert fourth.status_code == 429
    assert fourth.json()["error"] == "VelocityExceeded"


@pytest.mark.contract
def test_abuse_score_is_429():
    client = _client(abuse_default=0.95)
    r = _hold(client)
    assert r.status_code == 429
    assert r.json()["error"] == "AbuseSuspected"


@pytest.mark.contract
def test_payment_declined_is_402():
    client = _client(decline=True)
    booking = BookingOut.model_validate(_hold(client).json())
    r = client.post(f"/bookings/{booking.booking_id}/confirm")
    assert r.status_code == 402
    assert r.json()["error"] == "PaymentDeclined"


@pytest.mark.contract
def test_unreserved_is_pending_and_seatless(client):
    r = client.post(
        "/unreserved",
        json={"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 5,
              "passenger_id": "nic-1", "travel_class": "SECOND"},
    )
    assert r.status_code == 201
    booking = BookingOut.model_validate(r.json())
    assert booking.status == "PENDING"
    assert booking.seat_id == ""


@pytest.mark.contract
def test_settle_requires_the_counter_key(client):
    unreserved = client.post(
        "/unreserved",
        json={"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 3,
              "passenger_id": "nic-1", "travel_class": "SECOND"},
    )
    ref = BookingOut.model_validate(unreserved.json()).reference

    assert client.post("/admin/settle", json={"reference": ref}).status_code == 401

    ok = client.post(
        "/admin/settle", json={"reference": ref}, headers={"X-Counter-Key": COUNTER_KEY}
    )
    assert ok.status_code == 200
    invoice = InvoiceOut.model_validate(ok.json())
    assert invoice.status in ("CONFIRMED", "STANDING")


@pytest.mark.contract
def test_admin_lookup_behind_the_key(client):
    ref = BookingOut.model_validate(_hold(client).json()).reference
    assert client.get(f"/admin/bookings/{ref}").status_code == 401
    r = client.get(f"/admin/bookings/{ref}", headers={"X-Counter-Key": COUNTER_KEY})
    assert r.status_code == 200


@pytest.mark.contract
def test_waitlist_join_and_empty_promote(client):
    joined = client.post(
        "/waitlist",
        json={"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 3,
              "passenger_id": "p9", "travel_class": "SECOND"},
    )
    assert joined.status_code == 201
    WaitlistOut.model_validate(joined.json())

    promote = client.post(
        "/waitlist/promote",
        json={"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 3,
              "seat_id": "R1", "travel_class": "SECOND"},
    )
    assert promote.status_code == 200
    assert promote.json()["passenger_id"] == "p9"


@pytest.mark.contract
def test_idempotency_key_replays_the_same_booking(client):
    body = {"trip_id": "trip-1", "origin_seq": 0, "dest_seq": 5,
            "passenger_id": "nic-2", "travel_class": "SECOND"}
    headers = {"Idempotency-Key": "abc-123"}
    first = client.post("/unreserved", json=body, headers=headers)
    second = client.post("/unreserved", json=body, headers=headers)
    assert first.json()["reference"] == second.json()["reference"]


@pytest.mark.contract
def test_sse_stream_connects(client):
    with client.stream("GET", "/trips/trip-1/stream", params={"limit": 1}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.read().decode()
    assert "connected" in body
