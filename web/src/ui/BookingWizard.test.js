import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import BookingWizard from "./BookingWizard.svelte";
import { FakeApiClient } from "../adapters/api-client.fake.js";
import { FakeAvailabilityStream } from "../adapters/availability-stream.fake.js";
import { FakeStorage } from "../adapters/storage.fake.js";
import { FakeReceiptExporter } from "../adapters/receipt-exporter.fake.js";
import { DEMO_TRIP } from "../adapters/demo-trip.js";

function setup() {
  const api = new FakeApiClient({ trips: [DEMO_TRIP] });
  const stream = new FakeAvailabilityStream();
  const storage = new FakeStorage();
  const exporter = new FakeReceiptExporter();
  render(BookingWizard, { props: { api, stream, storage, exporter } });
  return { api, stream, storage, exporter };
}

describe("BookingWizard main path", () => {
  it("books a group of seats end to end, one linked as travelling with the other", async () => {
    setup();

    await userEvent.click(screen.getByRole("button", { name: /Reserve a seat/i }));

    const dateInput = screen.getByLabelText("Date");
    await fireEvent.input(dateInput, { target: { value: DEMO_TRIP.service_date } });
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    await userEvent.click(await screen.findByRole("button", { name: "Select" }));

    await userEvent.click(await screen.findByRole("button", { name: /Seat 1A/ }));
    await userEvent.click(screen.getByRole("button", { name: /Seat 1B/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    const names = screen.getAllByLabelText("Passenger name");
    const nics = screen.getAllByLabelText("NIC / passport");
    await userEvent.type(names[0], "Ann Perera");
    await userEvent.type(nics[0], "111111111V");
    await userEvent.type(names[1], "Sam Perera");
    await userEvent.type(nics[1], "222222222V");
    await userEvent.click(screen.getByRole("checkbox", { name: /Travelling with/ }));

    await userEvent.click(screen.getByRole("button", { name: "Reserve & pay" }));

    const references = await screen.findAllByText(/^SLR-/);
    expect(references).toHaveLength(2);
    expect(screen.getByText(/Travelling with Ann Perera/)).toBeInTheDocument();
  });
});
