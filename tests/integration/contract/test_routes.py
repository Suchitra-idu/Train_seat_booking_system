"""Every route exercised on the fake Container: each response is re-parsed through its
contract model (runtime schema validation, D13) and the domain-error -> HTTP mapping is
pinned. This is the whole HTTP surface, proven without infrastructure.
"""

import pytest
from fastapi.testclient import TestClient
from tests.integration.contract.conftest import COUNTER_KEY, _settings
from tests.integration.usecases._helpers import TODAY, make_trip

from slr.app.main import create_app
from slr.app.schemas import (
    BookingOut,
    LegAvailabilityOut,
    QuoteOut,
    ReceiptOut,
    TrainOptionOut,
    TripOut,
    VerifyOut,
)
from slr.app.wiring import wire_fake

COUNTER = {"X-Counter-Key": COUNTER_KEY}


def _client(**kw) -> TestClient:
    container = wire_fake((make_trip(service_date=TODAY),), **kw)
    return TestClient(create_app(container=container, settings=_settings()))


def _hold(client, seat_id="R1", origin=0, dest=3, passenger="p1", **extra):
    body = {
        "trip_id": "trip-1",
        "seat_id": seat_id,
        "origin_seq": origin,
        "dest_seq": dest,
        "passenger_id": passenger,
        "passenger_name": "Ann Perera",
        **extra,
    }
    return client.post("/bookings/hold", json=body)


def _sell(client, origin=0, dest=5, passenger="nic-1"):
    return client.post(
        "/admin/unreserved/sell",
        json={
            "trip_id": "trip-1",
            "origin_seq": origin,
            "dest_seq": dest,
            "passenger_id": passenger,
            "passenger_name": "Nimal Silva",
            "travel_class": "SECOND",
        },
        headers=COUNTER,
    )


@pytest.mark.contract
def test_health_is_ok(client):
    assert client.get("/").json()["status"] == "ok"


# ── search and reads ──────────────────────────────────────────────────────────


@pytest.mark.contract
def test_search_conforms(client):
    r = client.get("/search", params={"origin": "S0", "dest": "S3", "date": TODAY})
    assert r.status_code == 200
    options = [TrainOptionOut.model_validate(o) for o in r.json()]
    assert options[0].train_no == "1005"
    assert options[0].depart == "08:05"
    assert options[0].from_fare.cents > 0


@pytest.mark.contract
def test_search_on_a_day_with_no_service_is_empty_not_an_error(client):
    r = client.get("/search", params={"origin": "S0", "dest": "S3", "date": "1970-01-05"})
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.contract
def test_search_with_a_malformed_date_is_422(client):
    r = client.get("/search", params={"origin": "S0", "dest": "S3", "date": "not-a-date"})
    assert r.status_code == 422
    assert r.json()["error"] == "InvalidServiceDate"


@pytest.mark.contract
def test_search_with_the_same_station_twice_is_422(client):
    r = client.get("/search", params={"origin": "S0", "dest": "S0", "date": TODAY})
    assert r.status_code == 422
    assert r.json()["error"] == "InvalidLeg"


@pytest.mark.contract
def test_read_trip_carries_the_seat_map_geometry(client):
    r = client.get("/trips/trip-1")
    assert r.status_code == 200
    trip = TripOut.model_validate(r.json())
    assert trip.train_name == "Test Express"
    assert trip.coaches[0].columns == "1-0"
    assert trip.seats[0].row == 1
    assert trip.stops[0].depart == "08:05"


@pytest.mark.contract
def test_read_missing_trip_is_404(client):
    assert client.get("/trips/no-such-trip").status_code == 404


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


# ── the reserved lifecycle ────────────────────────────────────────────────────


@pytest.mark.contract
def test_hold_confirm_cancel_lifecycle(client):
    held = _hold(client)
    assert held.status_code == 201
    booking = BookingOut.model_validate(held.json())
    assert booking.status == "HELD"

    confirmed = client.post(f"/bookings/{booking.booking_id}/confirm")
    assert confirmed.status_code == 200
    receipt = ReceiptOut.model_validate(confirmed.json())
    assert receipt.status == "CONFIRMED"
    assert receipt.qr_payload == booking.reference
    assert receipt.seat_label == "1A"

    cancelled = client.post(f"/bookings/{booking.booking_id}/cancel")
    assert cancelled.status_code == 200
    assert BookingOut.model_validate(cancelled.json()).status == "CANCELLED"


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
def test_a_nameless_passenger_is_rejected_by_the_schema(client):
    r = _hold(client, passenger_name="")
    assert r.status_code == 422


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


# ── the public surface stops where D23/D24 say it does ────────────────────────


@pytest.mark.contract
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/unreserved"),
        ("post", "/waitlist"),
        ("post", "/waitlist/promote"),
        ("get", "/trips"),
    ],
)
def test_withdrawn_routes_are_gone(client, method, path):
    assert getattr(client, method)(path).status_code == 404


@pytest.mark.contract
def test_a_booking_cannot_be_read_back_without_the_counter_key(client):
    """A guessed reference must not surface a stranger's NIC (D24)."""
    ref = BookingOut.model_validate(_hold(client).json()).reference
    assert client.get(f"/bookings/{ref}").status_code == 404
    assert client.get(f"/admin/verify/{ref}").status_code == 401


# ── the counter (D21) ─────────────────────────────────────────────────────────


@pytest.mark.contract
def test_selling_unreserved_requires_the_counter_key(client):
    unauthorised = client.post(
        "/admin/unreserved/sell",
        json={
            "trip_id": "trip-1",
            "origin_seq": 0,
            "dest_seq": 5,
            "passenger_id": "nic-1",
            "passenger_name": "Nimal Silva",
            "travel_class": "SECOND",
        },
    )
    assert unauthorised.status_code == 401


@pytest.mark.contract
def test_counter_sale_returns_a_paid_receipt(client):
    r = _sell(client)
    assert r.status_code == 201
    receipt = ReceiptOut.model_validate(r.json())
    assert receipt.status in ("CONFIRMED", "STANDING")
    assert receipt.qr_payload == receipt.reference
    assert receipt.passenger_id == "nic-1"


@pytest.mark.contract
def test_verify_reads_a_sold_ticket_back(client):
    reference = ReceiptOut.model_validate(_sell(client).json()).reference
    r = client.get(f"/admin/verify/{reference}", headers=COUNTER)
    assert r.status_code == 200
    result = VerifyOut.model_validate(r.json())
    assert result.verdict == "VALID"
    assert result.valid
    assert result.ticket.passenger_id == "nic-1"


@pytest.mark.contract
def test_verify_of_a_forged_reference_is_404(client):
    r = client.get("/admin/verify/SLR-FORGED", headers=COUNTER)
    assert r.status_code == 404
    assert r.json()["error"] == "BookingNotFound"


@pytest.mark.contract
def test_idempotency_key_replays_the_same_sale(client):
    body = {
        "trip_id": "trip-1",
        "origin_seq": 0,
        "dest_seq": 5,
        "passenger_id": "nic-2",
        "passenger_name": "Nimal Silva",
        "travel_class": "SECOND",
    }
    headers = {**COUNTER, "Idempotency-Key": "abc-123"}
    first = client.post("/admin/unreserved/sell", json=body, headers=headers)
    second = client.post("/admin/unreserved/sell", json=body, headers=headers)
    assert first.json()["reference"] == second.json()["reference"]


@pytest.mark.contract
def test_sse_stream_connects(client):
    with client.stream("GET", "/trips/trip-1/stream", params={"limit": 1}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.read().decode()
    assert "connected" in body
