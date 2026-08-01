"""Real config (D11). Reads process env, with an optional override mapping on top.
A missing key raises KeyError, so a misconfiguration fails loud.
"""

from __future__ import annotations

import os
from collections.abc import Mapping


class EnvConfig:
    def __init__(self, overrides: Mapping[str, str] | None = None) -> None:
        self._values: dict[str, str] = dict(os.environ)
        if overrides:
            self._values.update(overrides)

    def get_int(self, key: str) -> int:
        return int(self._values[key])

    def get_float(self, key: str) -> float:
        return float(self._values[key])

    def get_str(self, key: str) -> str:
        return self._values[key]
