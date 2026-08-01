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
from slr.app.main import create_app
from slr.app.wiring import Container
from slr.domain.fares import Money
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Seat, Station, Trip

_STATIONS = (
    Station(code="FORT", name="Colombo Fort", seq=0, km=0.0),
    Station(code="RGM", name="Ragama", seq=1, km=14.0),
    Station(code="GPH", name="Gampaha", seq=2, km=28.0),
    Station(code="PDN", name="Peradeniya", seq=3, km=116.0),
    Station(code="NNO", name="Nanu Oya", seq=4, km=224.0),
    Station(code="BAD", name="Badulla", seq=5, km=292.0),
)

_SEATS = (
    Seat("F1", "A", CoachType.RESERVED, TravelClass.FIRST, 1),
    Seat("F2", "A", CoachType.RESERVED, TravelClass.FIRST, 2),
    Seat("R1", "B", CoachType.RESERVED, TravelClass.SECOND, 1),
    Seat("R2", "B", CoachType.RESERVED, TravelClass.SECOND, 2),
    Seat("R3", "B", CoachType.RESERVED, TravelClass.SECOND, 3),
    Seat("R4", "B", CoachType.RESERVED, TravelClass.SECOND, 4),
    Seat("U1", "C", CoachType.UNRESERVED, TravelClass.SECOND, 1),
    Seat("U2", "C", CoachType.UNRESERVED, TravelClass.SECOND, 2),
    Seat("U3", "C", CoachType.UNRESERVED, TravelClass.SECOND, 3),
)

DEMO_TRIP = Trip(
    trip_id="trip-1",
    route_code="CMB-BAD",
    service_date="2026-08-12",
    stations=_STATIONS,
    seats=_SEATS,
)


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
