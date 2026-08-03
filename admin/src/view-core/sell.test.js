import { describe, it, expect } from "vitest";
import { sellReady, sellRequest } from "./sell.js";

const train = { trip_id: "1005:2026-08-12", origin_seq: 0, dest_seq: 3 };

describe("sellReady", () => {
  it("is ready once a train, class and passenger are all filled in", () => {
    expect(
      sellReady({ train, travelClass: "SECOND", passengerId: "nic-1", passengerName: "Ann" }),
    ).toBe(true);
  });

  it("is not ready with a blank NIC or name", () => {
    expect(sellReady({ train, travelClass: "SECOND", passengerId: "  ", passengerName: "Ann" })).toBe(false);
    expect(sellReady({ train, travelClass: "SECOND", passengerId: "nic-1", passengerName: "" })).toBe(false);
  });

  it("is not ready with no train picked", () => {
    expect(sellReady({ train: null, travelClass: "SECOND", passengerId: "nic-1", passengerName: "Ann" })).toBe(false);
  });
});

describe("sellRequest", () => {
  it("shapes the API request from the train and passenger fields, trimmed", () => {
    const req = sellRequest({ train, travelClass: "SECOND", passengerId: " nic-1 ", passengerName: " Ann Perera " });
    expect(req).toEqual({
      tripId: train.trip_id,
      originSeq: 0,
      destSeq: 3,
      travelClass: "SECOND",
      passengerId: "nic-1",
      passengerName: "Ann Perera",
    });
  });
});
