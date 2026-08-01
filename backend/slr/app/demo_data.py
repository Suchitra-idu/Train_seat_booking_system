"""The demo trip that makes the stack explorable before the config-driven seed (P8).

One dated Colombo Fort -> Badulla service with a handful of reserved and unreserved seats,
shared by the zero-infra dev server and the compose seed step so both tell the same story.
Real station/coach/fare realism, driven entirely from config, lands in P8.
"""

from __future__ import annotations

from slr.domain.stations import Station
from slr.domain.values import CoachType, TravelClass
from slr.ports.repository import Seat, Trip

STATIONS = (
    Station(code="FORT", name="Colombo Fort", seq=0, km=0.0),
    Station(code="RGM", name="Ragama", seq=1, km=14.0),
    Station(code="GPH", name="Gampaha", seq=2, km=28.0),
    Station(code="PDN", name="Peradeniya", seq=3, km=116.0),
    Station(code="NNO", name="Nanu Oya", seq=4, km=224.0),
    Station(code="BAD", name="Badulla", seq=5, km=292.0),
)

SEATS = (
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
    stations=STATIONS,
    seats=SEATS,
)
