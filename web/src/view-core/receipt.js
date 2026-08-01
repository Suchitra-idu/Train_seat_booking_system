// L0 view-core: shape a ReceiptOut for the receipt screen (D24). Pure.

import { formatMoney } from "./money.js";

/** @param {object} receipt ReceiptOut */
export function receiptView(receipt) {
  return {
    reference: receipt.reference,
    qrPayload: receipt.qr_payload,
    passengerName: receipt.passenger_name,
    trainNo: receipt.train_no,
    trainName: receipt.train_name,
    serviceDate: receipt.service_date,
    origin: receipt.origin_name,
    dest: receipt.dest_name,
    depart: receipt.depart,
    arrive: receipt.arrive,
    seatLabel: receipt.seat_label,
    coach: receipt.coach,
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
