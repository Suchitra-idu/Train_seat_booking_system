// L0 view-core: shape a ReceiptOut for display (D24). Pure. Unlike the traveller app, the
// counter screen shows the passenger's NIC too, it's what the inspector checks against the
// ID in hand (D21), so it's part of this view-model even though the traveller never needs it.

import { formatMoney } from "./money.js";

/** @param {object} receipt ReceiptOut */
export function receiptView(receipt) {
  return {
    reference: receipt.reference,
    qrPayload: receipt.qr_payload,
    passengerId: receipt.passenger_id,
    passengerName: receipt.passenger_name,
    trainNo: receipt.train_no,
    trainName: receipt.train_name,
    serviceDate: receipt.service_date,
    origin: receipt.origin_name,
    dest: receipt.dest_name,
    depart: receipt.depart,
    arrive: receipt.arrive,
    travelClass: receipt.travel_class,
    seatLabel: receipt.seat_label,
    coach: receipt.coach,
    status: receipt.status,
    isStanding: receipt.status === "STANDING",
    standing: receipt.standing
      ? {
          afterStation: receipt.standing.after_station,
          seatLabel: receipt.standing.seat_label,
        }
      : null,
    fare: formatMoney(receipt.fare),
  };
}
