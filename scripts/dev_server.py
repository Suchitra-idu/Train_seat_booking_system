"""Zero-infra playground: the real FastAPI app on the in-memory fake, pre-seeded with a
demo Colombo Fort -> Badulla trip. No Docker, no Postgres — just run it and poke the API.

    uv run python scripts/dev_server.py        # -> http://localhost:8000/docs

State lives in the process, so a restart resets everything. This is for exploring the HTTP
surface; the real Postgres path and the concurrency proof are `make demo-concurrency`.
"""

from __future__ import annotations

import sys
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
from slr.app.demo_data import DEMO_TRIP
from slr.app.main import create_app
from slr.app.wiring import Container
from slr.domain.fares import Money


def build_app():
    """Real domain behaviour (dynamic distance/class fares, real abuse heuristic, live SSE)
    on an in-memory store — only the database is faked, so a restart resets state."""
    settings = load_settings()
    uow = MemoryUnitOfWork(trips=[DEMO_TRIP])
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
    return create_app(container=container, settings=settings)


if __name__ == "__main__":
    print("Demo trip 'trip-1' seeded (CMB-BAD, 2026-08-12). Docs at http://localhost:8000/docs")
    uvicorn.run(build_app(), host="127.0.0.1", port=8000, log_level="info")
