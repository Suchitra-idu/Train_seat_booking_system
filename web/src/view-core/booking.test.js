import { describe, it, expect } from "vitest";
import {
  initialBookingState,
  bookingReducer,
  isBusy,
  canRepick,
} from "./booking.js";

function run(actions, state = initialBookingState) {
  return actions.reduce(bookingReducer, state);
}

describe("bookingReducer happy path", () => {
  it("walks idle → quoted → held → confirmed", () => {
    const quote = { fare: { cents: 79460, currency: "LKR" } };
    const booking = { reference: "SLR-1", status: "HELD", seat_id: "R1" };
    const confirmed = { ...booking, status: "CONFIRMED" };

    let s = run([
      { type: "QUOTE_REQUESTED" },
      { type: "QUOTE_SUCCEEDED", quote },
      { type: "HOLD_REQUESTED" },
      { type: "HOLD_SUCCEEDED", booking },
    ]);
    expect(s.status).toBe("held");
    expect(s.quote).toBe(quote);
    expect(s.booking).toBe(booking);

    s = run([{ type: "CONFIRM_REQUESTED" }, { type: "CONFIRM_SUCCEEDED", booking: confirmed }], s);
    expect(s.status).toBe("confirmed");
    expect(s.booking.status).toBe("CONFIRMED");
  });
});

describe("bookingReducer conflict (409) handling", () => {
  it("drops the lost hold but keeps the quote and flags a re-pick", () => {
    const quote = { fare: { cents: 100, currency: "LKR" } };
    const s = run([
      { type: "QUOTE_SUCCEEDED", quote },
      { type: "HOLD_REQUESTED" },
      { type: "HOLD_CONFLICT", message: "gone" },
    ]);
    expect(s.status).toBe("error");
    expect(s.error).toEqual({ kind: "conflict", message: "gone" });
    expect(s.booking).toBeNull();
    expect(s.quote).toBe(quote);
    expect(canRepick(s)).toBe(true);
  });
});

describe("bookingReducer misc", () => {
  it("marks in-flight states busy", () => {
    expect(isBusy({ status: "holding" })).toBe(true);
    expect(isBusy({ status: "held" })).toBe(false);
  });
  it("FAILED carries a kind and message", () => {
    const s = bookingReducer(initialBookingState, { type: "FAILED", kind: "rate", message: "slow down" });
    expect(s.status).toBe("error");
    expect(s.error.kind).toBe("rate");
    expect(canRepick(s)).toBe(false);
  });
  it("RESET returns the initial state and ignores unknown actions", () => {
    const dirty = { status: "confirmed", booking: {}, quote: {}, error: null };
    expect(bookingReducer(dirty, { type: "RESET" })).toEqual(initialBookingState);
    expect(bookingReducer(dirty, { type: "NOPE" })).toBe(dirty);
  });
});
