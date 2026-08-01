import { describe, it, expect } from "vitest";
import { buildSeatMap, SEAT_STATUS, statusLabel, classLabel } from "./seatmap.js";

const TRIP = {
  trip_id: "trip-1",
  seats: [
    { seat_id: "R2", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 2 },
    { seat_id: "R1", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 1 },
    { seat_id: "F1", coach: "A", coach_type: "RESERVED", travel_class: "FIRST", number: 1 },
    { seat_id: "U1", coach: "C", coach_type: "UNRESERVED", travel_class: "SECOND", number: 1 },
  ],
};

const AVAIL = {
  seats: [
    { seat_id: "R1", available: true },
    { seat_id: "R2", available: false },
    { seat_id: "F1", available: true },
    { seat_id: "U1", available: true },
  ],
};

describe("buildSeatMap", () => {
  it("groups by coach (sorted) and orders seats by number", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    expect(map.coaches.map((c) => c.code)).toEqual(["A", "B", "C"]);
    const coachB = map.coaches.find((c) => c.code === "B");
    expect(coachB.seats.map((s) => s.id)).toEqual(["R1", "R2"]);
  });

  it("tags reserved seats free/taken and marks the selection", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL, selectedSeatId: "F1" });
    const byId = Object.fromEntries(map.coaches.flatMap((c) => c.seats).map((s) => [s.id, s]));
    expect(byId.R1.status).toBe(SEAT_STATUS.FREE);
    expect(byId.R1.selectable).toBe(true);
    expect(byId.R2.status).toBe(SEAT_STATUS.TAKEN);
    expect(byId.R2.selectable).toBe(false);
    expect(byId.F1.status).toBe(SEAT_STATUS.SELECTED);
  });

  it("never makes unreserved seats selectable", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    const u1 = map.coaches.flatMap((c) => c.seats).find((s) => s.id === "U1");
    expect(u1.status).toBe(SEAT_STATUS.UNRESERVED);
    expect(u1.selectable).toBe(false);
  });

  it("counts reserved-only free seats, excluding unreserved virtuals", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    expect(map.reservedTotal).toBe(3);
    expect(map.reservedFreeCount).toBe(2); // R1 + F1, not U1
    expect(map.hasUnreserved).toBe(true);
  });

  it("marks everything unknown before availability loads", () => {
    const map = buildSeatMap({ trip: TRIP, availability: null });
    const statuses = new Set(
      map.coaches.flatMap((c) => c.seats).filter((s) => s.coachType === "RESERVED").map((s) => s.status),
    );
    expect(statuses).toEqual(new Set([SEAT_STATUS.UNKNOWN]));
    expect(map.reservedFreeCount).toBe(0);
  });

  it("builds an accessible per-seat label", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    const r1 = map.coaches.flatMap((c) => c.seats).find((s) => s.id === "R1");
    expect(r1.label).toBe("Seat R1, 2nd class, available");
  });
});

describe("labels", () => {
  it("names statuses and classes", () => {
    expect(statusLabel("taken")).toBe("booked");
    expect(classLabel("FIRST")).toBe("1st class");
  });
});
