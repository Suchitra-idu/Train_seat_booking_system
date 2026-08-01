"""Emit the OpenAPI schema to contract/openapi.json — the source the frontend generates
its client from (D13). Run: `make emit-openapi`. A contract test fails if the committed
file drifts from the live app, so regenerating is part of changing a route.
"""

from __future__ import annotations

import json
from pathlib import Path

from slr.app.config import Settings
from slr.app.main import create_app
from slr.app.wiring import wire_fake

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "openapi.json"


def build_schema() -> dict:
    settings = Settings(
        database_url="fake",
        counter_key="counter-dev-key",
        currency="LKR",
        fare_strategy="dynamic",
        fare_rate_per_km_cents=685,
        policy={},
    )
    app = create_app(container=wire_fake(), settings=settings)
    return app.openapi()


def main() -> None:
    CONTRACT.write_text(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {CONTRACT}")


if __name__ == "__main__":
    main()
