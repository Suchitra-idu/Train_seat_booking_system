import { describe, it, expect } from "vitest";
import { buildSeatMap, SEAT_STATUS, statusLabel, classLabel } from "./seatmap.js";

const TRIP = {
  coaches: [
    { code: "A", coach_type: "RESERVED", travel_class: "SECOND", rows: 2, columns: "1-1", exit_rows: [1] },
    { code: "B", coach_type: "UNRESERVED", travel_class: "SECOND", rows: 1, columns: "1-0", exit_rows: [] },
  ],
  seats: [
    { seat_id: "A1A", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 1, row: 1, column: "A" },
    { seat_id: "A1B", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 2, row: 1, column: "B" },
    { seat_id: "A2A", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 3, row: 2, column: "A" },
    { seat_id: "A2B", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 4, row: 2, column: "B" },
    { seat_id: "B1A", coach: "B", coach_type: "UNRESERVED", travel_class: "SECOND", number: 1, row: 1, column: "A" },
  ],
};

const AVAILABILITY = {
  seats: [
    { seat_id: "A1A", coach: "A", travel_class: "SECOND", available: true },
    { seat_id: "A1B", coach: "A", travel_class: "SECOND", available: false },
    { seat_id: "A2A", coach: "A", travel_class: "SECOND", available: true },
    { seat_id: "A2B", coach: "A", travel_class: "SECOND", available: true },
  ],
};

describe("buildSeatMap main path", () => {
  it("lays seats into left/right blocks per row with exit-row breaks", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAILABILITY, selectedSeatIds: ["A2A", "A2B"] });
    const coachA = map.coaches.find((c) => c.code === "A");

    expect(coachA.rows).toHaveLength(2);
    expect(coachA.rows[0].left[0].id).toBe("A1A");
    expect(coachA.rows[0].right[0].id).toBe("A1B");
    expect(coachA.rows[0].exitAfter).toBe(true);

    expect(coachA.rows[0].left[0].status).toBe(SEAT_STATUS.FREE);
    expect(coachA.rows[0].right[0].status).toBe(SEAT_STATUS.TAKEN);
    // a group booking can hold more than one seat at once
    expect(coachA.rows[1].left[0].status).toBe(SEAT_STATUS.SELECTED);
    expect(coachA.rows[1].right[0].status).toBe(SEAT_STATUS.SELECTED);

    const coachB = map.coaches.find((c) => c.code === "B");
    expect(coachB.rows[0].left[0].status).toBe(SEAT_STATUS.UNRESERVED);
    expect(coachB.rows[0].left[0].selectable).toBe(false);

    expect(map.reservedTotal).toBe(4);
    expect(map.reservedFreeCount).toBe(3);
  });

  it("marks everything unknown before availability loads", () => {
    const map = buildSeatMap({ trip: TRIP, availability: null });
    expect(map.coaches[0].rows[0].left[0].status).toBe(SEAT_STATUS.UNKNOWN);
    expect(map.reservedFreeCount).toBe(0);
  });
});

describe("labels", () => {
  it("names statuses and classes", () => {
    expect(statusLabel("taken")).toBe("booked");
    expect(classLabel("FIRST")).toBe("1st class");
  });
});
