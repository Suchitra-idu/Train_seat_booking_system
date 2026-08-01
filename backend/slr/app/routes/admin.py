"""Ticket-counter routes behind the shared counter key (D21): sell and verify.

Sell is the only way an unreserved ticket comes into existence (D23). Verify is the only
way to read a booking back from a reference, which is what keeps a guessed reference from
leaking a passenger's NIC (D24).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from slr.app.config import Settings
from slr.app.deps import get_deps, get_settings, require_counter_key
from slr.app.schemas import ReceiptOut, SellUnreservedRequest, VerifyOut
from slr.domain.stations import Leg
from slr.usecases._deps import Deps
from slr.usecases.sell_unreserved import sell_unreserved
from slr.usecases.verify_ticket import verify_ticket

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_counter_key)]
)


@router.post("/unreserved/sell", response_model=ReceiptOut, status_code=201)
def sell(
    body: SellUnreservedRequest,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> ReceiptOut:
    receipt = sell_unreserved(
        deps,
        trip_id=body.trip_id,
        leg=Leg(body.origin_seq, body.dest_seq),
        passenger_id=body.passenger_id,
        passenger_name=body.passenger_name,
        travel_class=body.travel_class,
    )
    return ReceiptOut.of(receipt, settings.currency)


@router.get("/verify/{reference}", response_model=VerifyOut)
def verify(
    reference: str,
    deps: Deps = Depends(get_deps),
    settings: Settings = Depends(get_settings),
) -> VerifyOut:
    return VerifyOut.of(verify_ticket(deps, reference=reference), settings.currency)
