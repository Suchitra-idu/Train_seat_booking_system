"""The composition root. `create_app` wires a Container into the routes, mounts the
idempotency middleware, and registers the domain-error -> HTTP mapping. The module-level
`app` is what uvicorn and docker-compose run; tests build their own app with a fake
Container so the whole HTTP surface is exercised with zero infrastructure.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slr.app.config import Settings, load_settings
from slr.app.errors import register_error_handlers
from slr.app.middleware.idempotency import IdempotencyMiddleware
from slr.app.routes import api_router
from slr.app.wiring import Container, wire_real


def create_app(
    *, container: Container | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or load_settings()
    container = container or wire_real(settings)

    app = FastAPI(
        title="SLR Booking API",
        version="0.5.0",
        summary="Segment-based train seat booking (Colombo Fort to Badulla).",
    )
    app.state.container = container
    app.state.settings = settings
    # Order matters: the last-added middleware is outermost. CORS must wrap the
    # idempotency middleware, which rebuilds the response and would otherwise strip the
    # Access-Control-Allow-Origin header off a POST reply.
    app.add_middleware(IdempotencyMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_error_handlers(app)

    @app.get("/", tags=["health"])
    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "slr"}

    app.include_router(api_router)
    return app


app = create_app()
