"""Thin system pass: the assembled HTTP app over a real Postgres, searching and booking a
seat end to end. The composition root is the only code no other tier drives; this proves it
boots and that the GiST overlap constraint (D2) reaches all the way to a 409 at the API edge.
"""

import time

import pytest
from fastapi.testclient import TestClient
from tests.integration.usecases._helpers import make_trip

from slr.adapters.sqlalchemy_repo import upsert_trip
from slr.app.config import Settings
from slr.app.main import create_app
from slr.app.wiring import wire_real
from slr.domain.timetable import date_from_epoch

COUNTER_KEY = "sys-counter-key"
#: wire_real runs on the system clock, so the seeded trip has to be dated for real today.
TODAY = date_from_epoch(int(time.time()))


def _settings() -> Settings:
    return Settings(
        database_url="unused",
        counter_key=COUNTER_KEY,
        currency="LKR",
        fare_strategy="dynamic",
        fare_rate_per_km_cents=685,
        policy={
            "hold_ttl_seconds": "900",
            "max_seats_per_passenger": "4",
            "velocity_window_seconds": "600",
            "max_bookings_per_window": "5",
            "abuse_threshold": "0.8",
            "standing_capacity_per_coach": "2",
            "booking_window_days": "30",
            "utc_offset_minutes": "0",
            "class_mult_first": "2.0",
            "class_mult_second": "1.0",
            "class_mult_third": "0.7",
        },
    )


@pytest.fixture
def api(pg_session_factory) -> TestClient:
    seed = pg_session_factory()
    upsert_trip(seed, make_trip(service_date=TODAY))
    seed.commit()
    seed.close()
    container = wire_real(_settings(), session_factory=pg_session_factory)
    return TestClient(create_app(container=container, settings=_settings()))


def _hold(api, origin, dest, passenger):
    return api.post(
        "/bookings/hold",
        json={
            "trip_id": "trip-1",
            "seat_id": "R1",
            "origin_seq": origin,
            "dest_seq": dest,
            "passenger_id": passenger,
            "passenger_name": "Ann Perera",
        },
    )


@pytest.mark.integration
def test_books_a_seat_end_to_end_on_real_postgres(api):
    held = _hold(api, 0, 3, "p1")
    assert held.status_code == 201
    booking_id = held.json()["booking_id"]

    confirmed = api.post(f"/bookings/{booking_id}/confirm")
    assert confirmed.status_code == 200
    receipt = confirmed.json()
    assert receipt["status"] == "CONFIRMED"
    assert receipt["qr_payload"] == receipt["reference"]


@pytest.mark.integration
def test_overlapping_hold_is_rejected_by_the_constraint(api):
    assert _hold(api, 0, 3, "p1").status_code == 201
    clash = _hold(api, 1, 2, "p2")
    assert clash.status_code == 409
    assert clash.json()["error"] == "OverlapError"


@pytest.mark.integration
def test_the_search_route_finds_the_seeded_train(api):
    r = api.get("/search", params={"origin": "S0", "dest": "S3", "date": TODAY})
    assert r.status_code == 200
    assert [o["train_no"] for o in r.json()] == ["1005"]


@pytest.mark.integration
def test_the_counter_sells_and_then_verifies_the_same_ticket(api):
    sold = api.post(
        "/admin/unreserved/sell",
        json={
            "trip_id": "trip-1",
            "origin_seq": 0,
            "dest_seq": 5,
            "passenger_id": "nic-1",
            "passenger_name": "Nimal Silva",
            "travel_class": "SECOND",
        },
        headers={"X-Counter-Key": COUNTER_KEY},
    )
    assert sold.status_code == 201
    reference = sold.json()["reference"]

    verified = api.get(
        f"/admin/verify/{reference}", headers={"X-Counter-Key": COUNTER_KEY}
    )
    assert verified.status_code == 200
    assert verified.json()["verdict"] == "VALID"
    assert verified.json()["ticket"]["passenger_id"] == "nic-1"
