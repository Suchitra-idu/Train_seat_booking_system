"""Settings load for the composition root (D11).

Every operational parameter is env-driven with a working local default, so nothing is
hardcoded in a rule. The policy knobs the use-cases read arrive through the real
`EnvConfig` port under the lowercase keys `_support.py` expects; the rest (database URL,
counter key, fare rate, timetable path) drive wiring and the seeder.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from slr.adapters.env_config import EnvConfig

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMETABLE = str(REPO_ROOT / "config" / "timetable.json")

# Env var -> the Config key the use-cases read (see usecases/_support.py).
_POLICY_DEFAULTS: dict[str, tuple[str, str]] = {
    "hold_ttl_seconds": ("HOLD_TTL_SECONDS", "900"),
    "max_seats_per_passenger": ("SEAT_CAP_PER_PASSENGER", "6"),
    "velocity_window_seconds": ("VELOCITY_WINDOW_SECONDS", "600"),
    "max_bookings_per_window": ("BOOKING_VELOCITY_LIMIT", "10"),
    "abuse_threshold": ("ABUSE_THRESHOLD", "0.8"),
    "standing_capacity_per_coach": ("STANDING_CAPACITY", "250"),
    "booking_window_days": ("BOOKING_WINDOW_DAYS", "30"),
    "utc_offset_minutes": ("UTC_OFFSET_MINUTES", "330"),
    "class_mult_first": ("CLASS_MULT_FIRST", "2.0"),
    "class_mult_second": ("CLASS_MULT_SECOND", "1.0"),
    "class_mult_third": ("CLASS_MULT_THIRD", "0.7"),
}


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    counter_key: str
    currency: str
    fare_strategy: str
    fare_rate_per_km_cents: int
    timetable_path: str = DEFAULT_TIMETABLE
    #: Also served to the use-cases through the Config port; the seeder needs them
    #: directly, before any request exists.
    booking_window_days: int = 30
    utc_offset_minutes: int = 330
    cors_origins: tuple[str, ...] = ()
    policy: dict[str, str] = field(default_factory=dict)


def load_settings() -> Settings:
    policy = {
        key: os.getenv(env_name, default)
        for key, (env_name, default) in _POLICY_DEFAULTS.items()
    }
    origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+psycopg://slr:slr_local_dev@db:5432/slr"
        ),
        counter_key=os.getenv("COUNTER_KEY", "counter-dev-key"),
        currency=os.getenv("CURRENCY", "LKR"),
        fare_strategy=os.getenv("FARE_STRATEGY", "dynamic"),
        fare_rate_per_km_cents=int(os.getenv("FARE_RATE_PER_KM_CENTS", "685")),
        timetable_path=os.getenv("TIMETABLE_PATH", DEFAULT_TIMETABLE),
        booking_window_days=int(policy["booking_window_days"]),
        utc_offset_minutes=int(policy["utc_offset_minutes"]),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        policy=policy,
    )


def build_config(settings: Settings) -> EnvConfig:
    """A Config port serving the policy keys, backed by env with the loaded defaults."""
    return EnvConfig(settings.policy)
