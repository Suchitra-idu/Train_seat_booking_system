"""Seat-packing optimizer (D10), pure interval partitioning.

Occupancy is a set of half-open leg intervals; packing them onto the fewest seats is
interval-graph colouring, whose optimum is the maximum overlap depth. Greedy over
legs sorted by origin, reusing the earliest-freed seat, achieves that optimum. Used to
(1) auto-assign virtual seats in unreserved coaches (D3) and pick the seat that best
preserves contiguous availability, and (2) measure seat-km reclaimed vs whole-journey.
"""

from __future__ import annotations

import heapq
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from slr.domain.stations import Leg


def min_seats(legs: Sequence[Leg]) -> int:
    """Minimum seats to hold every leg without overlap = max overlap depth."""
    events: list[tuple[int, int]] = []
    for leg in legs:
        events.append((leg.origin_seq, +1))
        events.append((leg.dest_seq, -1))
    # At a shared coordinate a leg ending frees its seat before one starting claims it
    # (half-open, so adjacency reuses the seat): order -1 before +1.
    events.sort(key=lambda e: (e[0], e[1]))
    depth = peak = 0
    for _, delta in events:
        depth += delta
        peak = max(peak, depth)
    return peak


def pack(legs: Sequence[Leg]) -> list[int]:
    """Assign each leg a seat index (aligned to input order); optimal seat count."""
    order = sorted(range(len(legs)), key=lambda i: (legs[i].origin_seq, legs[i].dest_seq))
    assignment = [0] * len(legs)
    free: list[tuple[int, int]] = []  # (dest_seq freeing the seat, seat_index)
    seat_count = 0
    for i in order:
        leg = legs[i]
        if free and free[0][0] <= leg.origin_seq:
            _, seat = heapq.heappop(free)
        else:
            seat = seat_count
            seat_count += 1
        assignment[i] = seat
        heapq.heappush(free, (leg.dest_seq, seat))
    return assignment


def _occupied_span(seat_legs: Sequence[Leg]) -> int:
    return sum(leg.length for leg in seat_legs)


def choose_seat(seats: Sequence[Sequence[Leg]], leg: Leg) -> int | None:
    """Pick the seat that best preserves long contiguous availability.

    Best-fit: among seats with no overlapping leg, consolidate onto the fullest one so
    the emptier seats stay wholly free for future long legs. None if none is feasible.
    """
    best: int | None = None
    best_span = -1
    for idx, seat_legs in enumerate(seats):
        if any(leg.overlaps(existing) for existing in seat_legs):
            continue
        span = _occupied_span(seat_legs)
        if span > best_span:
            best, best_span = idx, span
    return best


def impact_seat_km(
    legs: Sequence[Leg], km_by_seq: Mapping[int, float], route_km: float
) -> float:
    """Seat-km reclaimed vs rigid whole-journey booking.

    Whole-journey locks a full seat (`route_km`) per booking; segment booking uses only
    the leg's km. The difference is resellable seat-km the old model would have wasted.
    """
    return sum(route_km - leg.distance_km(km_by_seq) for leg in legs)


@dataclass(frozen=True, slots=True)
class SeatOffer:
    """Seat `seat_index`, boarded at station `board_seq`, kept to the leg's end."""

    board_seq: int
    seat_index: int


def _frees_for_remainder(seat_legs: Sequence[Leg], origin: int, dest: int) -> int | None:
    """Earliest station in [origin, dest) where the seat is free to dest, else None."""
    blocking = [b for b in seat_legs if b.origin_seq < dest and b.dest_seq > origin]
    if not blocking:
        return origin
    frees_at = max(b.dest_seq for b in blocking)
    return frees_at if frees_at < dest else None


def predict_standing_seats(
    seats: Sequence[Sequence[Leg]], queue: Sequence[Leg]
) -> list[SeatOffer | None]:
    """Standing overflow allocation (D20). For each standing passenger in FIFO order,
    returns the earliest station and seat that serves the rest of their leg, or None to
    stand the whole way. A seat counts only if free from the boarding station to the
    destination. Earlier standees claim earlier-freeing seats. Ties go to the lower seat
    index.
    """
    occupancy = [list(seat) for seat in seats]
    offers: list[SeatOffer | None] = []
    for leg in queue:
        best: SeatOffer | None = None
        for idx, seat_legs in enumerate(occupancy):
            board = _frees_for_remainder(seat_legs, leg.origin_seq, leg.dest_seq)
            if board is not None and (best is None or board < best.board_seq):
                best = SeatOffer(board, idx)
        offers.append(best)
        if best is not None:
            occupancy[best.seat_index].append(Leg(best.board_seq, leg.dest_seq))
    return offers
