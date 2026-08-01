"""Ticket-counter routes behind the shared counter key (D21): look a booking up by its
reference/QR, then take payment and settle it into a seat or a standing prediction.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from slr.app.config import Settings
from slr.app.deps import get_deps, get_settings, require_counter_key
from slr.app.schemas import BookingOut, InvoiceOut, SettleRequest
from slr.usecases._deps import Deps
from slr.usecases.lookup_booking import lookup_booking
from slr.usecases.settle_at_counter import settle_at_counter

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_counter_key)]
)


@router.get("/bookings/{reference}", response_model=BookingOut)
def admin_lookup(reference: str, deps: Deps = Depends(get_deps)) -> BookingOut:
    return BookingOut.of(lookup_booking(deps, reference=reference))


@router.post("/settle", response_model=InvoiceOut)
def settle(
    body: SettleRequest,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> InvoiceOut:
    invoice = settle_at_counter(deps, reference=body.reference)
    return InvoiceOut.of(invoice, settings.currency)
