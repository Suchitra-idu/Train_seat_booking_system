import { describe, it, expect } from "vitest";
import { FakeApiClient } from "./api-client.fake.js";
import { DEMO_TRIP } from "./demo-trip.js";
import { ConflictError, ValidationError, PaymentError } from "../ports/errors.js";

const TRIP = DEMO_TRIP.trip_id;

const hold = (api, seatId, originSeq, destSeq, passengerId = "nic-1") =>
  api.hold({ tripId: TRIP, seatId, originSeq, destSeq, passengerId, passengerName: "Ann Perera" });

describe("FakeApiClient overlap invariant (D2)", () => {
  it("lets one physical seat serve two non-overlapping legs (segment resale)", async () => {
    const api = new FakeApiClient();
    await hold(api, "A1A", 0, 2, "alice");
    await expect(hold(api, "A1A", 2, 5, "bob")).resolves.toMatchObject({ status: "HELD" });
  });

  it("rejects an overlapping hold on the same seat with 409", async () => {
    const api = new FakeApiClient();
    await hold(api, "A1A", 0, 3, "alice");
    await expect(hold(api, "A1A", 1, 4, "eve")).rejects.toBeInstanceOf(ConflictError);
  });

  it("reflects a hold in per-leg availability", async () => {
    const api = new FakeApiClient();
    await hold(api, "A1A", 0, 3);
    const avail = await api.availability(TRIP, { originSeq: 1, destSeq: 2 });
    expect(avail.seats.find((s) => s.seat_id === "A1A").available).toBe(false);
    expect(avail.seats.find((s) => s.seat_id === "A1B").available).toBe(true);
  });
});

describe("FakeApiClient rules", () => {
  it("refuses to hold an unreserved seat", async () => {
    const api = new FakeApiClient();
    await expect(hold(api, "B1A", 0, 3)).rejects.toBeInstanceOf(ValidationError);
  });

  it("rejects a reversed leg", async () => {
    const api = new FakeApiClient();
    await expect(hold(api, "A1A", 3, 0)).rejects.toBeInstanceOf(ValidationError);
  });

  it("can force a payment decline for the confirm path", async () => {
    const api = new FakeApiClient({ declinePayment: true });
    const b = await hold(api, "A1A", 0, 3);
    await expect(api.confirm(b.booking_id)).rejects.toBeInstanceOf(PaymentError);
  });
});

describe("FakeApiClient confirm and cancel", () => {
  it("confirm returns a receipt with a QR payload and the seat label", async () => {
    const api = new FakeApiClient();
    const b = await hold(api, "A1A", 0, 3);
    const receipt = await api.confirm(b.booking_id);
    expect(receipt.status).toBe("CONFIRMED");
    expect(receipt.qr_payload).toBe(receipt.reference);
    expect(receipt.seat_label).toBe("1A");
  });

  it("cancel frees the seat for the next booker", async () => {
    const api = new FakeApiClient();
    const b = await hold(api, "A1A", 0, 3, "alice");
    await api.cancel(b.booking_id);
    await expect(hold(api, "A1A", 0, 3, "bob")).resolves.toMatchObject({ status: "HELD" });
  });
});
