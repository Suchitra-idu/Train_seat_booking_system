"""Identity ports. Opaque ids and human-facing booking references."""

from __future__ import annotations

from typing import Protocol


class IdGen(Protocol):
    def new_id(self) -> str:
        """A fresh, unique opaque identifier."""
        ...


class ReferenceGen(Protocol):
    def new_reference(self) -> str:
        """A fresh, unique booking reference such as 'SLR-000123'."""
        ...
