"""Domain error -> HTTP status mapping (D14). One handler turns any typed rule violation
into a clean 4xx with a stable body; invalid input never corrupts state, it fails loud.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from slr.domain.errors import (
    AntiAbuseError,
    BookingNotFound,
    CoachFull,
    DomainError,
    IllegalTransition,
    InvalidLeg,
    NoFeasibleSeat,
    OverlapError,
    PaymentDeclined,
    SeatNotBookable,
)

# Most-specific first is irrelevant here: resolution walks the exception's MRO, so a
# SeatCapExceeded matches AntiAbuseError (429) before the DomainError (400) fallback.
_STATUS: dict[type[DomainError], int] = {
    OverlapError: 409,
    IllegalTransition: 409,
    NoFeasibleSeat: 409,
    CoachFull: 409,
    AntiAbuseError: 429,
    PaymentDeclined: 402,
    BookingNotFound: 404,
    SeatNotBookable: 422,
    InvalidLeg: 422,
    DomainError: 400,
}


def status_for(exc: DomainError) -> int:
    for klass in type(exc).__mro__:
        if klass in _STATUS:
            return _STATUS[klass]
    return 400


def _body(exc: Exception, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return _body(exc, status_for(exc))

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError) -> JSONResponse:
        # A ValueError that escaped the domain (e.g. lookup with neither key) is bad input.
        return _body(exc, 422)

    @app.exception_handler(KeyError)
    async def _missing(_: Request, exc: KeyError) -> JSONResponse:
        # The repositories raise KeyError for an unknown trip/booking id; policy config
        # keys are seeded at load, so a request-time KeyError is always "not found".
        return JSONResponse(
            status_code=404,
            content={"error": "NotFound", "detail": str(exc)},
        )
