import { describe, it, expect, vi } from "vitest";
import { RealApiClient } from "./api-client.real.js";
import {
  ConflictError,
  RateLimitError,
  ValidationError,
  PaymentError,
  NotFoundError,
  SchemaError,
} from "../ports/errors.js";
import { DEMO_TRIP } from "./demo-trip.js";

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? "" : JSON.stringify(body)),
  };
}

const bookingBody = {
  booking_id: "b-1",
  reference: "SLR-000001",
  trip_id: "trip-1",
  seat_id: "R1",
  origin_seq: 0,
  dest_seq: 3,
  passenger_id: "alice",
  travel_class: "SECOND",
  status: "HELD",
  held_until: 1900,
  created_at: 1000,
};

describe("RealApiClient happy path + contract validation", () => {
  it("returns a validated trip list", async () => {
    const fetchImpl = vi.fn(async () => response(200, [DEMO_TRIP]));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    const trips = await api.listTrips({ routeCode: "CMB-BAD", serviceDate: "2026-08-12" });
    expect(trips).toHaveLength(1);
    const [url] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://api/trips?route_code=CMB-BAD&service_date=2026-08-12");
  });

  it("sends the idempotency key and a snake_case body on hold", async () => {
    const fetchImpl = vi.fn(async () => response(201, bookingBody));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await api.hold(
      { tripId: "trip-1", seatId: "R1", originSeq: 0, destSeq: 3, passengerId: "alice", travelClass: "SECOND" },
      { idempotencyKey: "k-1" },
    );
    const [, init] = fetchImpl.mock.calls[0];
    expect(init.headers["idempotency-key"]).toBe("k-1");
    expect(JSON.parse(init.body)).toMatchObject({ trip_id: "trip-1", seat_id: "R1", origin_seq: 0 });
  });

  it("throws SchemaError when a 2xx body violates the contract", async () => {
    const fetchImpl = vi.fn(async () => response(201, { booking_id: "b-1" }));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await expect(
      api.hold({ tripId: "t", seatId: "R1", originSeq: 0, destSeq: 3, passengerId: "a", travelClass: "SECOND" }),
    ).rejects.toBeInstanceOf(SchemaError);
  });
});

describe("RealApiClient maps HTTP status to typed errors", () => {
  const cases = [
    [409, ConflictError],
    [429, RateLimitError],
    [422, ValidationError],
    [402, PaymentError],
    [404, NotFoundError],
  ];
  for (const [status, Err] of cases) {
    it(`${status} → ${Err.name}`, async () => {
      const fetchImpl = vi.fn(async () => response(status, { error: Err.name, detail: "nope" }));
      const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
      await expect(api.confirm("b-1")).rejects.toBeInstanceOf(Err);
    });
  }

  it("carries the server detail onto the error", async () => {
    const fetchImpl = vi.fn(async () => response(409, { error: "OverlapError", detail: "seat R1 taken" }));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await expect(api.confirm("b-1")).rejects.toMatchObject({ detail: "seat R1 taken" });
  });
});
