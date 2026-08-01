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

    const options = await api.searchTrains({
      originCode: "FORT",
      destCode: "KDY",
      serviceDate: DEMO_TRIP.service_date,
    });
    validateResponse(RESPONSE_SCHEMA.searchTrains, options);

    validateResponse(RESPONSE_SCHEMA.getTrip, await api.getTrip(DEMO_TRIP.trip_id));
    validateResponse(RESPONSE_SCHEMA.availability, await api.availability(DEMO_TRIP.trip_id, leg));
    validateResponse(
      RESPONSE_SCHEMA.quote,
      await api.quote({ tripId: DEMO_TRIP.trip_id, ...leg, travelClass: "SECOND" }),
    );

    const held = await api.hold({
      tripId: DEMO_TRIP.trip_id,
      seatId: "A1A",
      ...leg,
      passengerId: "nic-1",
      passengerName: "Ann Perera",
    });
    validateResponse(RESPONSE_SCHEMA.hold, held);
    validateResponse(RESPONSE_SCHEMA.confirm, await api.confirm(held.booking_id));

    const another = await api.hold({
      tripId: DEMO_TRIP.trip_id,
      seatId: "A1B",
      ...leg,
      passengerId: "nic-2",
      passengerName: "Bee Silva",
    });
    validateResponse(RESPONSE_SCHEMA.cancel, await api.cancel(another.booking_id));
  });

  it("rejects a response that violates the contract", () => {
    expect(() =>
      validateResponse(RESPONSE_SCHEMA.hold, { booking_id: "b1" /* missing required fields */ }),
    ).toThrow(SchemaError);
  });
});
