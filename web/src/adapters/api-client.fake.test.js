import { describe, it, expect } from "vitest";
import { FakeApiClient } from "./api-client.fake.js";
import { ConflictError, ValidationError, PaymentError } from "../ports/errors.js";

const hold = (api, seatId, originSeq, destSeq, passengerId = "p") =>
  api.hold({ tripId: "trip-1", seatId, originSeq, destSeq, passengerId, travelClass: "SECOND" });

describe("FakeApiClient overlap invariant (D2)", () => {
  it("lets one physical seat serve two non-overlapping legs (segment resale)", async () => {
    const api = new FakeApiClient();
    await hold(api, "R1", 0, 2, "alice");
    await expect(hold(api, "R1", 2, 5, "bob")).resolves.toMatchObject({ status: "HELD" });
  });

  it("rejects an overlapping hold on the same seat with 409", async () => {
    const api = new FakeApiClient();
    await hold(api, "R1", 0, 3, "alice");
    await expect(hold(api, "R1", 1, 4, "eve")).rejects.toBeInstanceOf(ConflictError);
  });

  it("reflects a hold in per-leg availability", async () => {
    const api = new FakeApiClient();
    await hold(api, "R1", 0, 3);
    const avail = await api.availability("trip-1", { originSeq: 1, destSeq: 2 });
    expect(avail.seats.find((s) => s.seat_id === "R1").available).toBe(false);
    expect(avail.seats.find((s) => s.seat_id === "R2").available).toBe(true);
  });
});

describe("FakeApiClient rules", () => {
  it("refuses to hold an unreserved seat", async () => {
    const api = new FakeApiClient();
    await expect(hold(api, "U1", 0, 3)).rejects.toBeInstanceOf(ValidationError);
  });

  it("rejects a reversed leg", async () => {
    const api = new FakeApiClient();
    await expect(hold(api, "R1", 3, 0)).rejects.toBeInstanceOf(ValidationError);
  });

  it("can force a payment decline for the confirm path", async () => {
    const api = new FakeApiClient({ declinePayment: true });
    const b = await hold(api, "R1", 0, 3);
    await expect(api.confirm(b.booking_id)).rejects.toBeInstanceOf(PaymentError);
  });
});

describe("FakeApiClient cancel promotes the waitlist (D16)", () => {
  it("promotes the oldest compatible waiter onto the freed seat", async () => {
    const api = new FakeApiClient();
    const held = await hold(api, "R1", 0, 5, "alice");
    await api.joinWaitlist({
      tripId: "trip-1",
      originSeq: 0,
      destSeq: 5,
      passengerId: "bob",
      travelClass: "SECOND",
    });
    const { cancelled, promoted } = await api.cancel(held.booking_id);
    expect(cancelled.status).toBe("CANCELLED");
    expect(promoted).toMatchObject({ seat_id: "R1", passenger_id: "bob", status: "HELD" });
  });
});

describe("FakeApiClient unreserved NIC-only flow (D3)", () => {
  it("issues a seatless PENDING booking with a reference", async () => {
    const api = new FakeApiClient();
    const b = await api.unreserved({
      tripId: "trip-1",
      originSeq: 0,
      destSeq: 5,
      passengerId: "nic-771234567",
      travelClass: "SECOND",
    });
    expect(b).toMatchObject({ status: "PENDING", seat_id: "" });
    expect(b.reference).toMatch(/^SLR-/);
  });
});
