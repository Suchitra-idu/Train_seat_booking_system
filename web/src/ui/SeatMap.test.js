import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import SeatMap from "./SeatMap.svelte";
import { buildSeatMap } from "../view-core/seatmap.js";

const TRIP = {
  coaches: [
    { code: "A", coach_type: "RESERVED", travel_class: "SECOND", rows: 1, columns: "1-1", exit_rows: [] },
    { code: "B", coach_type: "UNRESERVED", travel_class: "SECOND", rows: 1, columns: "1-0", exit_rows: [] },
  ],
  seats: [
    { seat_id: "A1A", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 1, row: 1, column: "A" },
    { seat_id: "A1B", coach: "A", coach_type: "RESERVED", travel_class: "SECOND", number: 2, row: 1, column: "B" },
    { seat_id: "B1A", coach: "B", coach_type: "UNRESERVED", travel_class: "SECOND", number: 1, row: 1, column: "A" },
  ],
};
const AVAIL = {
  seats: [
    { seat_id: "A1A", coach: "A", travel_class: "SECOND", available: true },
    { seat_id: "A1B", coach: "A", travel_class: "SECOND", available: false },
  ],
};

describe("SeatMap main path", () => {
  it("toggles a free seat and calls ontoggle", async () => {
    const ontoggle = vi.fn();
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    render(SeatMap, { props: { map, ontoggle } });

    await userEvent.click(screen.getByRole("button", { name: /Seat 1A/ }));
    expect(ontoggle).toHaveBeenCalledWith("A1A");
  });

  it("disables a booked seat and switches coaches", async () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    render(SeatMap, { props: { map, ontoggle: () => {} } });
    expect(screen.getByRole("button", { name: /Seat 1B/ })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Coach B" }));
    expect(screen.getByRole("button", { name: /Seat 1A.*unreserved/ })).toBeDisabled();
  });
});
