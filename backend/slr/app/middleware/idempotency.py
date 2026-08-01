"""Idempotency at the HTTP edge (D9). A duplicate submit — a double-click, a retried
POST — carrying the same `Idempotency-Key` header replays the first response instead of
running the intent twice. This complements the use-case `reference` replay: this stops
the second request ever reaching a handler.

In-memory and per-process, which is right for the single-node demo; a shared store is the
production swap. Only POST requests with the header are cached; GET and SSE pass straight
through.
"""

from __future__ import annotations

import threading
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

_HEADER = "idempotency-key"


class _Cache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[int, bytes, str]] = {}

    def get(self, key: str) -> tuple[int, bytes, str] | None:
        with self._lock:
            return self._store.get(key)

    def put(self, key: str, value: tuple[int, bytes, str]) -> None:
        with self._lock:
            self._store[key] = value


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._cache = _Cache()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        key = request.headers.get(_HEADER)
        if request.method != "POST" or not key:
            return await call_next(request)

        cache_key = f"{request.method} {request.url.path} {key}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            status, body, media = cached
            return Response(content=body, status_code=status, media_type=media)

        # call_next hands back a streaming response; buffer it so the body can be replayed.
        response = cast(StreamingResponse, await call_next(request))
        chunks: list[bytes] = [
            chunk.encode() if isinstance(chunk, str) else bytes(chunk)
            async for chunk in response.body_iterator
        ]
        body = b"".join(chunks)
        self._cache.put(
            cache_key,
            (response.status_code, body, response.media_type or "application/json"),
        )
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
