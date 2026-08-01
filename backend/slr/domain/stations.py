"""Stations and legs as half-open intervals over the line's station sequence.

A leg is `[origin_seq, dest_seq)` on integer sequence positions; km positions drive
fares (fares.py), sequence positions drive occupancy. Two legs on one seat conflict
iff their intervals overlap, the single rule the Postgres EXCLUDE constraint mirrors
in P3 (D2). Adjacent legs `[A,B)` and `[B,C)` do not overlap, so both book: that is
segment resale.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from slr.domain.errors import InvalidLeg


@dataclass(frozen=True, slots=True)
class Station:
    code: str
    name: str
    seq: int
    km: float


@dataclass(frozen=True, slots=True)
class Leg:
    origin_seq: int
    dest_seq: int

    def __post_init__(self) -> None:
        if self.origin_seq < 0:
            raise InvalidLeg(f"negative origin sequence: {self.origin_seq}")
        if self.dest_seq <= self.origin_seq:
            raise InvalidLeg(
                f"leg must move forward: [{self.origin_seq}, {self.dest_seq})"
            )

    @property
    def length(self) -> int:
        """Number of station-hops the leg spans."""
        return self.dest_seq - self.origin_seq

    def overlaps(self, other: Leg) -> bool:
        # Half-open intersection: touching endpoints ([A,B) & [B,C)) do not overlap.
        return self.origin_seq < other.dest_seq and other.origin_seq < self.dest_seq

    def is_adjacent(self, other: Leg) -> bool:
        return self.dest_seq == other.origin_seq or other.dest_seq == self.origin_seq

    def contains(self, seq: int) -> bool:
        return self.origin_seq <= seq < self.dest_seq

    def distance_km(self, km_by_seq: Mapping[int, float]) -> float:
        return km_by_seq[self.dest_seq] - km_by_seq[self.origin_seq]


def km_index(stations: Iterable[Station]) -> dict[int, float]:
    """Map each station's sequence position to its km from origin."""
    return {s.seq: s.km for s in stations}

