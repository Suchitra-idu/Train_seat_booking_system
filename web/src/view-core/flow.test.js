import { describe, it, expect } from "vitest";
import { flowReducer, initialFlowState, canGoBack } from "./flow.js";

describe("flowReducer main path", () => {
  it("walks landing -> search -> trains -> seats -> passenger -> receipt for a group of seats", () => {
    let s = flowReducer(initialFlowState, { type: "START" });
    expect(s.step).toBe("search");

    s = flowReducer(s, {
      type: "SEARCHED",
      journey: { originCode: "FORT", destCode: "BAD", serviceDate: "2026-08-12" },
    });
    expect(s.step).toBe("trains");

    s = flowReducer(s, { type: "TRAIN_SELECTED", train: { trip_id: "trip-1" } });
    expect(s.step).toBe("seats");

    s = flowReducer(s, { type: "SEAT_TOGGLED", seatId: "A1A" });
    s = flowReducer(s, { type: "SEAT_TOGGLED", seatId: "A1B" });
    expect(s.seatIds).toEqual(["A1A", "A1B"]);

    s = flowReducer(s, { type: "SEATS_CONFIRMED" });
    expect(s.step).toBe("passenger");
    expect(s.passengers).toMatchObject({
      A1A: { name: "", nic: "", childOfSeatId: null },
      A1B: { name: "", nic: "", childOfSeatId: null },
    });
    expect(canGoBack(s)).toBe(true);

    s = flowReducer(s, { type: "PASSENGER_UPDATED", seatId: "A1A", patch: { name: "Ann", nic: "111" } });
    s = flowReducer(s, {
      type: "PASSENGER_UPDATED",
      seatId: "A1B",
      patch: { name: "Sam", nic: "222", childOfSeatId: "A1A" },
    });
    expect(s.passengers.A1B.childOfSeatId).toBe("A1A");

    s = flowReducer(s, {
      type: "BOOKED",
      tickets: [
        { seatId: "A1A", childOfSeatId: null, receipt: { reference: "SLR-1" } },
        { seatId: "A1B", childOfSeatId: "A1A", receipt: { reference: "SLR-2" } },
      ],
    });
    expect(s.step).toBe("receipt");
    expect(canGoBack(s)).toBe(false);
  });

  it("toggling a seat off drops its passenger and un-links anyone marked as its child", () => {
    let s = { ...initialFlowState, step: "passenger", seatIds: ["A1A", "A1B"] };
    s = flowReducer(s, { type: "SEATS_CONFIRMED" });
    s = flowReducer(s, {
      type: "PASSENGER_UPDATED",
      seatId: "A1B",
      patch: { childOfSeatId: "A1A" },
    });

    s = flowReducer(s, { type: "SEAT_TOGGLED", seatId: "A1A" }); // remove the parent seat
    expect(s.seatIds).toEqual(["A1B"]);
    expect(s.passengers.A1A).toBeUndefined();
    expect(s.passengers.A1B.childOfSeatId).toBeNull();
  });

  it("a seat conflict during group checkout drops just that seat", () => {
    let s = { ...initialFlowState, step: "passenger", seatIds: ["A1A", "A1B"] };
    s = flowReducer(s, {
      type: "SEAT_REMOVED_CONFLICT",
      seatId: "A1B",
      message: "That seat was just taken.",
    });
    expect(s.step).toBe("seats");
    expect(s.seatIds).toEqual(["A1A"]);
    expect(s.error).toMatch(/just taken/);
  });

  it("back does nothing from landing or receipt", () => {
    expect(flowReducer(initialFlowState, { type: "BACK" }).step).toBe("landing");
    const receipted = { ...initialFlowState, step: "receipt" };
    expect(flowReducer(receipted, { type: "BACK" }).step).toBe("receipt");
  });
});
