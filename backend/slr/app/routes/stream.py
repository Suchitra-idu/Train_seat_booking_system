"""Server-Sent Events availability stream per trip (D7). The use-cases publish seat/leg
deltas to the SSE broker; this endpoint drains one subscriber queue into the response so
clients grey out seats live. One-way is all availability needs, no WebSocket.

The generator polls the in-process queue and stops as soon as the client disconnects, so
a dropped connection never leaks a subscriber or a hung task.
"""

from __future__ import annotations

import json
import queue
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from slr.app.deps import get_container
from slr.app.wiring import Container

router = APIRouter(tags=["stream"])

_POLL_SECONDS = 0.25


@router.get("/trips/{trip_id}/stream")
def trip_stream(
    trip_id: str,
    request: Request,
    container: Container = Depends(get_container),
    limit: int | None = Query(default=None, ge=1),
) -> StreamingResponse:
    """`limit` caps the number of frames then closes the stream; omit it for a live feed.
    It exists so a client (and the contract test) can take a bounded read."""
    publisher = container.availability
    subscription = publisher.subscribe()

    async def events() -> AsyncIterator[str]:
        sent = 0
        try:
            yield ": connected\n\n"
            sent += 1
            while limit is None or sent < limit:
                if await request.is_disconnected():
                    break
                try:
                    event = subscription.get_nowait()
                except queue.Empty:
                    await anyio.sleep(_POLL_SECONDS)
                    continue
                if event.trip_id != trip_id:
                    continue
                payload = json.dumps(
                    {
                        "trip_id": event.trip_id,
                        "seat_id": event.seat_id,
                        "origin_seq": event.leg.origin_seq,
                        "dest_seq": event.leg.dest_seq,
                        "status": event.status.value,
                    }
                )
                yield f"event: availability\ndata: {payload}\n\n"
                sent += 1
        finally:
            publisher.unsubscribe(subscription)

    return StreamingResponse(events(), media_type="text/event-stream")
