import { describe, it, expect } from "vitest";
import { verifyView, notFoundView } from "./verify.js";

const ticket = {
  reference: "SLR-000001",
  qr_payload: "SLR-000001",
  passenger_id: "nic-1",
  passenger_name: "Ann Perera",
  train_no: "1005",
  train_name: "Podi Menike",
  service_date: "2026-08-12",
  origin_name: "Colombo Fort",
  dest_name: "Kandy",
  depart: "05:55",
  arrive: "08:47",
  travel_class: "SECOND",
  coach: "B",
  seat_label: "1A",
  status: "CONFIRMED",
  standing: null,
  fare: { cents: 12000, currency: "LKR" },
};

describe("verifyView", () => {
  it("shows a valid, confirmed ticket as valid with a success tone", () => {
    const view = verifyView({ verdict: "VALID", valid: true, ticket });
    expect(view.valid).toBe(true);
    expect(view.tone).toBe("success");
    expect(view.ticket.passengerId).toBe("nic-1");
    expect(view.ticket.seatLabel).toBe("1A");
  });

  it("marks an unpaid hold as not valid with a warning tone", () => {
    const view = verifyView({ verdict: "UNPAID", valid: false, ticket });
    expect(view.valid).toBe(false);
    expect(view.tone).toBe("warning");
  });
});

describe("notFoundView", () => {
  it("is the display for a forged or mistyped reference", () => {
    const view = notFoundView();
    expect(view.valid).toBe(false);
    expect(view.tone).toBe("error");
    expect(view.ticket).toBeNull();
  });
});
