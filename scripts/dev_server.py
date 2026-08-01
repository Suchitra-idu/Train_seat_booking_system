"""Zero-infra playground: the real FastAPI app on the in-memory fake, seeded from the
same timetable config compose uses. No Docker, no Postgres, just run it and poke the API.

    uv run python scripts/dev_server.py        # -> http://localhost:8000/docs

State lives in the process, so a restart resets everything. This is for exploring the HTTP
surface; the real Postgres path and the concurrency proof are `make demo-concurrency`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Put the source tree on the path so `uv run python scripts/dev_server.py` works directly,
# not only through `make dev` (which exports PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import uvicorn

from slr.adapters.dynamic_fare import DynamicFare
from slr.adapters.heuristic_abuse import HeuristicAbuse
from slr.adapters.log_notifier import LogNotifier
from slr.adapters.memory_repo import MemoryUnitOfWork
from slr.adapters.mock_payment import MockPayment
from slr.adapters.sse_publisher import SsePublisher
from slr.adapters.system_clock import SystemClock
from slr.adapters.uuid_ids import UuidIdGen, UuidReferenceGen
from slr.app.config import build_config, load_settings
from slr.app.main import create_app
from slr.app.timetable_config import load_timetable
from slr.app.wiring import Container
from slr.domain.fares import Money
from slr.domain.timetable import date_from_epoch


def build_app():
    """Real domain behaviour (dynamic distance/class fares, real abuse heuristic, live SSE)
    on an in-memory store, seeded with the live booking window from config/timetable.json.
    Only the database is faked, so a restart resets state."""
    settings = load_settings()
    today = date_from_epoch(int(time.time()), utc_offset_minutes=settings.utc_offset_minutes)
    trips = load_timetable(settings.timetable_path).trips_for_window(
        today, settings.booking_window_days
    )
    uow = MemoryUnitOfWork(trips=trips)
    container = Container(
        uow_factory=lambda: uow,
        clock=SystemClock(),
        ids=UuidIdGen(),
        references=UuidReferenceGen(),
        fares=DynamicFare(Money(settings.fare_rate_per_km_cents)),
        config=build_config(settings),
        notifier=LogNotifier(),
        availability=SsePublisher(),
        abuse=HeuristicAbuse(),
        payment=MockPayment(),
    )
    print(f"Seeded {len(trips)} trips over {settings.booking_window_days} days from {today}.")
    return create_app(container=container, settings=settings)


if __name__ == "__main__":
    print("Docs at http://localhost:8000/docs")
    uvicorn.run(build_app(), host="127.0.0.1", port=8000, log_level="info")
