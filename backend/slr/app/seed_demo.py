"""Compose seed step (P6a bridge): put the demo trip into Postgres so `docker compose up`
yields a stack the web app can book against end to end. Idempotent - a re-run is a no-op.
The full config-driven seed of real stations/coaches/fares is P8; this is the minimal slice
that makes the frontend runnable now.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slr.adapters.orm import TripRow
from slr.adapters.sqlalchemy_repo import insert_trip
from slr.app.config import load_settings
from slr.app.demo_data import DEMO_TRIP


def main() -> None:
    settings = load_settings()
    engine = create_engine(settings.database_url)
    session = sessionmaker(bind=engine)()
    try:
        if session.get(TripRow, DEMO_TRIP.trip_id) is not None:
            print(f"seed: trip {DEMO_TRIP.trip_id!r} already present, nothing to do")
            return
        insert_trip(session, DEMO_TRIP)
        print(f"seed: inserted demo trip {DEMO_TRIP.trip_id!r} ({DEMO_TRIP.route_code})")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
