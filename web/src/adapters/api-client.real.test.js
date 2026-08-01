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
  passenger_name: "Alice Perera",
  travel_class: "SECOND",
  status: "HELD",
  fare: { cents: 12000, currency: "LKR" },
  held_until: 1900,
  created_at: 1000,
};

const receiptBody = {
  reference: "SLR-000001",
  qr_payload: "SLR-000001",
  booking_id: "b-1",
  passenger_id: "alice",
  passenger_name: "Alice Perera",
  trip_id: "trip-1",
  route_code: "CMB-BAD",
  train_no: "1005",
  train_name: "Podi Menike",
  service_date: "2026-08-12",
  origin_code: "FORT",
  origin_name: "Colombo Fort",
  origin_seq: 0,
  dest_code: "KDY",
  dest_name: "Kandy",
  dest_seq: 3,
  depart: "05:55",
  arrive: "08:47",
  duration_min: 172,
  travel_class: "SECOND",
  fare: { cents: 12000, currency: "LKR" },
  status: "CONFIRMED",
  issued_at: 1000,
  coach: "A",
  seat_label: "1A",
  standing: null,
};

describe("RealApiClient happy path + contract validation", () => {
  it("returns validated search results", async () => {
    const fetchImpl = vi.fn(async () => response(200, []));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await api.searchTrains({ originCode: "FORT", destCode: "BAD", serviceDate: "2026-08-12" });
    const [url] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://api/search?origin=FORT&dest=BAD&date=2026-08-12");
  });

  it("returns a validated trip", async () => {
    const fetchImpl = vi.fn(async () => response(200, DEMO_TRIP));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    const trip = await api.getTrip("1005:2026-08-12");
    expect(trip.train_no).toBe("1005");
  });

  it("sends the idempotency key and a snake_case body on hold", async () => {
    const fetchImpl = vi.fn(async () => response(201, bookingBody));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await api.hold(
      { tripId: "trip-1", seatId: "R1", originSeq: 0, destSeq: 3, passengerId: "alice", passengerName: "Alice Perera" },
      { idempotencyKey: "k-1" },
    );
    const [, init] = fetchImpl.mock.calls[0];
    expect(init.headers["idempotency-key"]).toBe("k-1");
    expect(JSON.parse(init.body)).toMatchObject({ trip_id: "trip-1", seat_id: "R1", origin_seq: 0 });
  });

  it("confirm returns a validated receipt", async () => {
    const fetchImpl = vi.fn(async () => response(200, receiptBody));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    const receipt = await api.confirm("b-1");
    expect(receipt.qr_payload).toBe("SLR-000001");
  });

  it("throws SchemaError when a 2xx body violates the contract", async () => {
    const fetchImpl = vi.fn(async () => response(201, { booking_id: "b-1" }));
    const api = new RealApiClient({ baseUrl: "http://api", fetchImpl });
    await expect(
      api.hold({ tripId: "t", seatId: "R1", originSeq: 0, destSeq: 3, passengerId: "a", passengerName: "A" }),
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
