"""Anti-tout predicates (D9), parity with SLR's Aug-2025 verified-ID policy. Pure
functions over a passenger's history and an injected `now` (epoch seconds); the clock
lives in a port, never here. Limits/caps are parameters (D11). Boundaries are the whole
point, so they are tested exactly.
"""

import pytest

from slr.domain.policy import named_passenger_ok, within_seat_cap, within_velocity

# ── seat cap ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.parametrize(
    "active,requested,cap,ok",
    [
        (0, 1, 4, True),
        (3, 1, 4, True),   # lands exactly on the cap
        (4, 1, 4, False),  # one over
        (2, 2, 4, True),   # multi-seat request that just fits
        (2, 3, 4, False),  # multi-seat request that overflows
    ],
)
def test_within_seat_cap_boundaries(active, requested, cap, ok):
    assert within_seat_cap(active, requested, cap) is ok


@pytest.mark.unit
@pytest.mark.parametrize("requested,cap", [(0, 4), (-1, 4)])
def test_seat_cap_rejects_nonsense_quantity(requested, cap):
    with pytest.raises(ValueError):
        within_seat_cap(0, requested, cap)


# ── booking velocity ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_within_velocity_counts_only_the_trailing_window():
    now = 1000
    window = 60
    # three bookings inside (940, 1000], one older at 900 (outside)
    times = [900, 950, 980, 1000]
    assert within_velocity(times, now, window_seconds=window, limit=4) is True   # 3 < 4
    assert within_velocity(times, now, window_seconds=window, limit=3) is False  # 3 == 3


@pytest.mark.unit
def test_velocity_window_edge_is_exclusive():
    now = 1000
    # a booking exactly `window` seconds old is outside the trailing window
    assert within_velocity([940], now, window_seconds=60, limit=1) is True
    assert within_velocity([941], now, window_seconds=60, limit=1) is False


@pytest.mark.unit
def test_velocity_rejects_nonsense_config():
    with pytest.raises(ValueError):
        within_velocity([], 1000, window_seconds=0, limit=3)
    with pytest.raises(ValueError):
        within_velocity([], 1000, window_seconds=60, limit=-1)


# ── named passenger (non-transferable ticket) ─────────────────────────────────


@pytest.mark.unit
def test_named_passenger_matches_case_and_whitespace_insensitively():
    assert named_passenger_ok("199512345678", "199512345678") is True
    assert named_passenger_ok("  199512345678 ", "199512345678") is True
    assert named_passenger_ok("95X1234v", "95x1234V") is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "ticket,boarding",
    [("199512345678", "200098765432"), ("", "x"), ("x", ""), (" ", "x")],
)
def test_named_passenger_mismatch_or_empty_fails(ticket, boarding):
    assert named_passenger_ok(ticket, boarding) is False
