import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import BookingFlow from "./BookingFlow.svelte";
import { FakeApiClient } from "../adapters/api-client.fake.js";
import { FakeAvailabilityStream } from "../adapters/availability-stream.fake.js";
import { FakeStorage } from "../adapters/storage.fake.js";
import { DEMO_TRIP } from "../adapters/demo-trip.js";

function mountFlow(api) {
  return render(BookingFlow, {
    props: {
      api,
      stream: new FakeAvailabilityStream(),
      storage: new FakeStorage(),
      routeCode: "CMB-BAD",
      serviceDate: "2026-08-12",
    },
  });
}

async function fillPassenger() {
  await userEvent.type(screen.getByLabelText("Passenger name"), "Alice Perera");
  await userEvent.type(screen.getByLabelText("NIC / passport"), "200012345678");
}

describe("BookingFlow reserved happy path", () => {
  it("selects a seat then reserves and pays in one action", async () => {
    const api = new FakeApiClient();
    mountFlow(api);

    await userEvent.click(await screen.findByRole("button", { name: /Seat R1/ }));
    // fare is quoted into the sidebar
    expect(await screen.findByText(/Rs /)).toBeInTheDocument();

    await fillPassenger();
    await userEvent.click(screen.getByRole("button", { name: /Reserve & pay/ }));

    expect(await screen.findByText(/Ticket booked/)).toBeInTheDocument();
    expect(screen.getByText(/^SLR-/)).toBeInTheDocument();
  });
});

describe("BookingFlow sold-out → waitlist", () => {
  it("offers the waitlist when no reserved seat is free", async () => {
    const api = new FakeApiClient();
    // Take every reserved seat over the default leg [0,5).
    for (const seat of DEMO_TRIP.seats.filter((s) => s.coach_type === "RESERVED")) {
      await api.hold({
        tripId: "trip-1",
        seatId: seat.seat_id,
        originSeq: 0,
        destSeq: 5,
        passengerId: "holder",
        travelClass: "SECOND",
      });
    }
    mountFlow(api);

    const join = await screen.findByRole("button", { name: /Join the waitlist/ });
    await fillPassenger();
    await userEvent.click(join);
    expect(await screen.findByText(/on the waitlist/i)).toBeInTheDocument();
  });
});

describe("BookingFlow unreserved NIC-only flow", () => {
  it("books a seatless PENDING ticket with a reference", async () => {
    const api = new FakeApiClient();
    mountFlow(api);
    await screen.findByRole("button", { name: /Seat R1/ }); // wait for load

    await userEvent.click(screen.getByRole("button", { name: /^Unreserved$/ }));
    await fillPassenger();
    await userEvent.click(screen.getByRole("button", { name: /Book unreserved/ }));

    const panel = await screen.findByText(/Reference/);
    expect(within(panel.closest("div")).getByText(/^SLR-/)).toBeInTheDocument();
  });
});
