"""FastAPI dependency providers: reach the container, mint a per-request Deps, and guard
the admin routes with the shared counter key (D21).
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request

from slr.app.config import Settings
from slr.app.wiring import Container
from slr.usecases._deps import Deps


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_deps(container: Container = Depends(get_container)) -> Iterator[Deps]:
    deps = container.deps()
    try:
        yield deps
    finally:
        close = getattr(deps.uow, "close", None)
        if callable(close):
            close()


def require_counter_key(
    x_counter_key: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if not secrets.compare_digest(x_counter_key, settings.counter_key):
        raise HTTPException(status_code=401, detail="invalid counter key")
