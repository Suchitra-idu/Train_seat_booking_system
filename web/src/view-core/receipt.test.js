import { describe, it, expect } from "vitest";
import { receiptView } from "./receipt.js";

describe("receiptView main path", () => {
  it("shapes a seated receipt", () => {
    const v = receiptView({
      reference: "SLR-7K3M-92",
      qr_payload: "SLR-7K3M-92",
      passenger_name: "Ann Perera",
      train_no: "1005",
      train_name: "Podi Menike",
      service_date: "2026-08-12",
      origin_name: "Colombo Fort",
      dest_name: "Badulla",
      depart: "05:55",
      arrive: "15:55",
      seat_label: "3A",
      coach: "B",
      status: "CONFIRMED",
      standing: null,
      fare: { cents: 120000, currency: "LKR" },
    });
    expect(v.reference).toBe("SLR-7K3M-92");
    expect(v.seatLabel).toBe("3A");
    expect(v.isStanding).toBe(false);
    expect(v.standing).toBeNull();
    expect(v.fare).toBe("Rs 1,200.00");
  });

  it("shapes a standing receipt with the D20 prediction", () => {
    const v = receiptView({
      reference: "SLR-1",
      qr_payload: "SLR-1",
      passenger_name: "Nimal Silva",
      train_no: "1005",
      train_name: "Podi Menike",
      service_date: "2026-08-12",
      origin_name: "Colombo Fort",
      dest_name: "Badulla",
      depart: "05:55",
      arrive: "15:55",
      seat_label: null,
      coach: null,
      status: "STANDING",
      standing: { after_station: "Kandy", seat_label: "5C" },
      fare: { cents: 90000, currency: "LKR" },
    });
    expect(v.isStanding).toBe(true);
    expect(v.standing).toEqual({ afterStation: "Kandy", seatLabel: "5C" });
  });
});
