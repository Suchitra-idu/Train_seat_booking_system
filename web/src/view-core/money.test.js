import { describe, it, expect } from "vitest";
import { formatMoney, formatKm } from "./money.js";

describe("formatMoney", () => {
  it("renders LKR minor units as Rs with grouping and 2 decimals", () => {
    expect(formatMoney({ cents: 123450, currency: "LKR" })).toBe("Rs 1,234.50");
    expect(formatMoney({ cents: 685 })).toBe("Rs 6.85");
    expect(formatMoney({ cents: 0 })).toBe("Rs 0.00");
    expect(formatMoney({ cents: 100000000 })).toBe("Rs 1,000,000.00");
  });

  it("falls back to the currency code for non-LKR", () => {
    expect(formatMoney({ cents: 500, currency: "USD" })).toBe("USD 5.00");
  });

  it("handles negatives and junk safely", () => {
    expect(formatMoney({ cents: -250 })).toBe("-Rs 2.50");
    expect(formatMoney(null)).toBe("-");
    expect(formatMoney({ cents: NaN })).toBe("-");
  });
});

describe("formatKm", () => {
  it("rounds to at most one decimal", () => {
    expect(formatKm(292)).toBe("292 km");
    expect(formatKm(115.96)).toBe("116 km");
    expect(formatKm(14.5)).toBe("14.5 km");
    expect(formatKm(NaN)).toBe("-");
  });
});
