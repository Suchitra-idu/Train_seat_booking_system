import { describe, it, expect } from "vitest";
import { freeSeatIds, isSeatAvailable, freeCount, isSoldOut } from "./availability.js";

const AVAIL = {
  trip_id: "trip-1",
  origin_seq: 0,
  dest_seq: 3,
  free_count: 2,
  seats: [
    { seat_id: "R1", coach: "B", travel_class: "SECOND", available: true },
    { seat_id: "R2", coach: "B", travel_class: "SECOND", available: false },
    { seat_id: "R3", coach: "B", travel_class: "SECOND", available: true },
  ],
};

describe("availability", () => {
  it("collects the free seat ids", () => {
    expect([...freeSeatIds(AVAIL)]).toEqual(["R1", "R3"]);
    expect([...freeSeatIds(null)]).toEqual([]);
  });
  it("answers per-seat availability", () => {
    expect(isSeatAvailable(AVAIL, "R1")).toBe(true);
    expect(isSeatAvailable(AVAIL, "R2")).toBe(false);
  });
  it("prefers the server free_count but can derive it", () => {
    expect(freeCount(AVAIL)).toBe(2);
    expect(freeCount({ seats: AVAIL.seats })).toBe(2);
  });
  it("detects sold out only for a loaded, empty leg", () => {
    expect(isSoldOut(AVAIL)).toBe(false);
    expect(isSoldOut({ free_count: 0, seats: [] })).toBe(true);
    expect(isSoldOut(null)).toBe(false);
  });
});
