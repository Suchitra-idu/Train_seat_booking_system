"""Deterministic id and reference generators for tests."""

from __future__ import annotations


class SeqIdGen:
    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n}"


class SeqReferenceGen:
    def __init__(self, prefix: str = "SLR", width: int = 6) -> None:
        self._prefix = prefix
        self._width = width
        self._n = 0

    def new_reference(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n:0{self._width}d}"
