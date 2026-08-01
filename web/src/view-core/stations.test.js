import { describe, it, expect } from "vitest";
import {
  orderedStations,
  stationBySeq,
  isValidLeg,
  legLabel,
  legDistanceKm,
  formatServiceDate,
} from "./stations.js";

const STATIONS = [
  { code: "FORT", name: "Colombo Fort", seq: 0, km: 0 },
  { code: "GPH", name: "Gampaha", seq: 2, km: 28 },
  { code: "RGM", name: "Ragama", seq: 1, km: 14 },
  { code: "BAD", name: "Badulla", seq: 5, km: 292 },
];

describe("stations", () => {
  it("orders by sequence", () => {
    expect(orderedStations(STATIONS).map((s) => s.code)).toEqual([
      "FORT", "RGM", "GPH", "BAD",
    ]);
  });

  it("looks up by seq", () => {
    expect(stationBySeq(STATIONS, 2).code).toBe("GPH");
    expect(stationBySeq(STATIONS, 9)).toBeNull();
  });
});

describe("isValidLeg", () => {
  it("accepts a forward half-open leg between real stations", () => {
    expect(isValidLeg({ originSeq: 0, destSeq: 5 }, STATIONS)).toBe(true);
  });
  it("rejects reversed, empty, off-route, and non-integer legs", () => {
    expect(isValidLeg({ originSeq: 5, destSeq: 0 }, STATIONS)).toBe(false);
    expect(isValidLeg({ originSeq: 2, destSeq: 2 }, STATIONS)).toBe(false);
    expect(isValidLeg({ originSeq: 0, destSeq: 9 }, STATIONS)).toBe(false);
    expect(isValidLeg({ originSeq: 0.5, destSeq: 2 }, STATIONS)).toBe(false);
    expect(isValidLeg(null, STATIONS)).toBe(false);
  });
});

describe("legLabel + distance", () => {
  it("labels the leg by station names", () => {
    expect(legLabel(STATIONS, { originSeq: 0, destSeq: 2 })).toBe(
      "Colombo Fort → Gampaha",
    );
    expect(legLabel(STATIONS, { originSeq: 0, destSeq: 9 })).toBe("-");
  });
  it("spans km between origin and destination", () => {
    expect(legDistanceKm(STATIONS, { originSeq: 1, destSeq: 5 })).toBe(278);
    expect(legDistanceKm(STATIONS, { originSeq: 0, destSeq: 9 })).toBe(0);
  });
});

describe("formatServiceDate", () => {
  it("formats an ISO date without reading the clock", () => {
    expect(formatServiceDate("2026-08-12")).toBe("12 Aug 2026");
    expect(formatServiceDate("not-a-date")).toBe("not-a-date");
    expect(formatServiceDate(null)).toBe("-");
  });
});
