import { describe, it, expect } from "vitest";
import { RESPONSE_SCHEMA } from "../ports/api-client.js";
import { validateResponse, SchemaError } from "./schema.js";
import { FakeApiClient } from "./api-client.fake.js";
import { DEMO_TRIP } from "./demo-trip.js";

// The fake is only a trustworthy stand-in for the real client if it speaks the same
// contract. Drive every method and validate its output against the OpenAPI component the
// port binds it to (D13). This is what lets the UI integration tests run on the fake.
describe("FakeApiClient conforms to the OpenAPI contract", () => {
  const leg = { originSeq: 0, destSeq: 3 };

  it("every response validates against its bound schema", async () => {
    const api = new FakeApiClient();
    const q = { routeCode: DEMO_TRIP.route_code, serviceDate: DEMO_TRIP.service_date };

    validateResponse(RESPONSE_SCHEMA.listTrips, await api.listTrips(q));
    validateResponse(RESPONSE_SCHEMA.availability, await api.availability("trip-1", leg));
    validateResponse(
      RESPONSE_SCHEMA.quote,
      await api.quote({ tripId: "trip-1", ...leg, travelClass: "SECOND" }),
    );

    const held = await api.hold({
      tripId: "trip-1",
      seatId: "R1",
      ...leg,
      passengerId: "alice",
      travelClass: "SECOND",
    });
    validateResponse(RESPONSE_SCHEMA.hold, held);
    validateResponse(RESPONSE_SCHEMA.confirm, await api.confirm(held.booking_id));
    validateResponse(RESPONSE_SCHEMA.lookup, await api.lookup(held.reference));
    validateResponse(RESPONSE_SCHEMA.impact, await api.impact("trip-1"));

    const pending = await api.unreserved({
      tripId: "trip-1",
      ...leg,
      passengerId: "nic-77",
      travelClass: "SECOND",
    });
    validateResponse(RESPONSE_SCHEMA.unreserved, pending);

    const wl = await api.joinWaitlist({
      tripId: "trip-1",
      ...leg,
      passengerId: "bob",
      travelClass: "SECOND",
    });
    validateResponse(RESPONSE_SCHEMA.joinWaitlist, wl);

    const cancel = await api.cancel(held.booking_id);
    validateResponse(RESPONSE_SCHEMA.cancel, cancel);
  });

  it("rejects a response that violates the contract", () => {
    expect(() =>
      validateResponse(RESPONSE_SCHEMA.hold, { booking_id: "b1" /* missing required fields */ }),
    ).toThrow(SchemaError);
  });
});
