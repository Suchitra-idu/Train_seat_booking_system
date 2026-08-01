import { describe, it, expect } from "vitest";
import { trainRows } from "./trains.js";

describe("trainRows main path", () => {
  it("shapes a TrainOptionOut into a display row", () => {
    const [row] = trainRows([
      {
        trip_id: "1005:2026-08-12",
        train_no: "1005",
        train_name: "Podi Menike",
        depart: "05:55",
        arrive: "15:55",
        duration_min: 600,
        free_seats: 12,
        from_fare: { cents: 120000, currency: "LKR" },
        classes: [
          { travel_class: "SECOND", free_seats: 12, fare: { cents: 120000, currency: "LKR" } },
        ],
      },
    ]);
    expect(row.trainNo).toBe("1005");
    expect(row.duration).toBe("10h");
    expect(row.soldOut).toBe(false);
    expect(row.classes[0].label).toBe("2nd class");
  });
});
