"""Config port. Typed access to operational parameters (D11). Missing key raises KeyError."""

from __future__ import annotations

from typing import Protocol


class Config(Protocol):
    def get_int(self, key: str) -> int:
        ...

    def get_float(self, key: str) -> float:
        ...

    def get_str(self, key: str) -> str:
        ...
