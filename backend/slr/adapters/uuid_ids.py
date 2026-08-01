"""Real id and reference generators. Collision-free via uuid4."""

from __future__ import annotations

import uuid


class UuidIdGen:
    def new_id(self) -> str:
        return str(uuid.uuid4())


class UuidReferenceGen:
    def __init__(self, prefix: str = "SLR") -> None:
        self._prefix = prefix

    def new_reference(self) -> str:
        return f"{self._prefix}-{uuid.uuid4().hex[:12].upper()}"
