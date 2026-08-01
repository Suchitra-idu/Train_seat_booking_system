"""Fixture config. Serves a fixed dict. A missing key raises KeyError."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FixtureConfig:
    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = dict(values)

    def get_int(self, key: str) -> int:
        return int(self._values[key])

    def get_float(self, key: str) -> float:
        return float(self._values[key])

    def get_str(self, key: str) -> str:
        return str(self._values[key])
