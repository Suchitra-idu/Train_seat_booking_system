import { describe, it, expect, vi } from "vitest";
import { RealApiClient } from "./api-client.real.js";
import { NotFoundError } from "../ports/errors.js";

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? "" : JSON.stringify(body)),
  };
}

const receiptBody = {
  reference: "SLR-000001",
  qr_payload: "SLR-000001",
  booking_id: "b-1",
  passenger_id: "nic-1",
  passenger_name: "Ann Perera",
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
  coach: "B",
  seat_label: "1A",
  standing: null,
};

describe("RealApiClient", () => {
  it("sends the counter key on sell and verify, but not on the public search route", async () => {
    const fetchImpl = vi.fn(async () => response(200, receiptBody));
    const api = new RealApiClient({ baseUrl: "http://api", counterKey: "secret", fetchImpl });

    await api.sell({
      tripId: "trip-1",
      originSeq: 0,
      destSeq: 3,
      travelClass: "SECOND",
      passengerId: "nic-1",
      passengerName: "Ann Perera",
    });
    expect(fetchImpl.mock.calls[0][1].headers["x-counter-key"]).toBe("secret");

    fetchImpl.mockResolvedValueOnce(response(200, { verdict: "VALID", valid: true, ticket: receiptBody }));
    await api.verify("SLR-000001");
    expect(fetchImpl.mock.calls[1][1].headers["x-counter-key"]).toBe("secret");

    fetchImpl.mockResolvedValueOnce(response(200, []));
    await api.searchTrains({ originCode: "FORT", destCode: "KDY", serviceDate: "2026-08-12" });
    expect(fetchImpl.mock.calls[2][1].headers["x-counter-key"]).toBeUndefined();
  });

  it("maps a 404 to NotFoundError", async () => {
    const fetchImpl = vi.fn(async () => response(404, { error: "BookingNotFound", detail: "no such reference" }));
    const api = new RealApiClient({ baseUrl: "http://api", counterKey: "secret", fetchImpl });
    await expect(api.verify("SLR-FORGED")).rejects.toThrow(NotFoundError);
  });
});
