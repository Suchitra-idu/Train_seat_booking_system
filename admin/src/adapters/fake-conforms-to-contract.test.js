import { describe, it, expect } from "vitest";
import { RESPONSE_SCHEMA } from "../ports/api-client.js";
import { validateResponse, SchemaError } from "./schema.js";
import { FakeApiClient } from "./api-client.fake.js";
import { DEMO_TRIP } from "./demo-trip.js";

// The fake is only a trustworthy stand-in for the real client if it speaks the same
// contract (D13). Drive every method and validate its output against the OpenAPI
// component the port binds it to, this is what lets the UI integration tests run on it.
describe("FakeApiClient conforms to the OpenAPI contract", () => {
  it("every response validates against its bound schema", async () => {
    const api = new FakeApiClient();

    const options = await api.searchTrains({
      originCode: "FORT",
      destCode: "KDY",
      serviceDate: DEMO_TRIP.service_date,
    });
    validateResponse(RESPONSE_SCHEMA.searchTrains, options);

    const receipt = await api.sell({
      tripId: DEMO_TRIP.trip_id,
      originSeq: 0,
      destSeq: 3,
      travelClass: "SECOND",
      passengerId: "nic-1",
      passengerName: "Ann Perera",
    });
    validateResponse(RESPONSE_SCHEMA.sell, receipt);
    validateResponse(RESPONSE_SCHEMA.verify, await api.verify(receipt.reference));
  });

  it("rejects a response that violates the contract", () => {
    expect(() =>
      validateResponse(RESPONSE_SCHEMA.sell, { reference: "SLR-1" /* missing required fields */ }),
    ).toThrow(SchemaError);
  });
});
