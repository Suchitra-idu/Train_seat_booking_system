import { describe, it, expect } from "vitest";
import { formatDuration, isoDate } from "./time.js";

describe("time main path", () => {
  it("formats a duration in hours and minutes", () => {
    expect(formatDuration(600)).toBe("10h");
    expect(formatDuration(65)).toBe("1h 5m");
    expect(formatDuration(45)).toBe("45m");
  });

  it("formats a Date as an ISO date", () => {
    expect(isoDate(new Date(2026, 7, 12))).toBe("2026-08-12");
  });
});
