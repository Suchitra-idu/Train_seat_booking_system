"""Compose seed step: expand the timetable config into dated trips (D22).

Idempotent by construction, a trip's id is `{pattern_code}:{date}`, so re-running only
inserts the dates that rolled into the window since last time. `docker compose up` can be
run any number of times and the second run is a no-op.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from slr.adapters.sqlalchemy_repo import upsert_trip
from slr.app.config import Settings, load_settings
from slr.app.timetable_config import load_timetable
from slr.domain.timetable import date_from_epoch


def seed(session: Session, settings: Settings, *, today: str) -> int:
    """Insert every trip in the booking window. Returns how many were new."""
    timetable = load_timetable(settings.timetable_path)
    trips = timetable.trips_for_window(today, settings.booking_window_days)
    return sum(1 for trip in trips if upsert_trip(session, trip))


def main() -> None:
    import time  # the composition root is where the clock is allowed to be read

    settings = load_settings()
    today = date_from_epoch(int(time.time()), utc_offset_minutes=settings.utc_offset_minutes)
    engine = create_engine(settings.database_url)
    session = sessionmaker(bind=engine)()
    try:
        inserted = seed(session, settings, today=today)
        session.commit()
        print(
            f"seed: {inserted} new trips for {today} "
            f"+{settings.booking_window_days}d from {settings.timetable_path}"
        )
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
