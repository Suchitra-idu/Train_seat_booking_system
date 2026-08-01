import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import SeatMap from "./SeatMap.svelte";
import { buildSeatMap } from "../view-core/seatmap.js";

const TRIP = {
  seats: [
    { seat_id: "R1", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 1 },
    { seat_id: "R2", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 2 },
    { seat_id: "U1", coach: "C", coach_type: "UNRESERVED", travel_class: "SECOND", number: 1 },
  ],
};
const AVAIL = {
  seats: [
    { seat_id: "R1", available: true },
    { seat_id: "R2", available: false },
    { seat_id: "U1", available: true },
  ],
};

describe("SeatMap", () => {
  it("selects a free seat and calls onselect", async () => {
    const onselect = vi.fn();
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    render(SeatMap, { props: { map, onselect } });

    await userEvent.click(screen.getByRole("button", { name: /Seat R1/ }));
    expect(onselect).toHaveBeenCalledWith("R1");
  });

  it("disables booked and unreserved seats", () => {
    const map = buildSeatMap({ trip: TRIP, availability: AVAIL });
    render(SeatMap, { props: { map, onselect: () => {} } });
    expect(screen.getByRole("button", { name: /Seat R2/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Seat U1/ })).toBeDisabled();
  });
});
