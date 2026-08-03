import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import App from "./App.svelte";
import { RealApiClient } from "../adapters/api-client.real.js";
import { RealReceiptExporter } from "../adapters/receipt-exporter.real.js";
import { FakeApiClient } from "../adapters/api-client.fake.js";
import { FakeReceiptExporter } from "../adapters/receipt-exporter.fake.js";
import { DEMO_TRIP } from "../adapters/demo-trip.js";

// App.svelte wires the real adapters itself (it's the composition root), so this test
// substitutes the fake ApiClient/ReceiptExporter at the module level, the same seam the
// contract test proves is faithful (fake-conforms-to-contract.test.js).
vi.mock("../adapters/api-client.real.js", () => ({
  RealApiClient: vi.fn(),
}));
vi.mock("../adapters/receipt-exporter.real.js", () => ({
  RealReceiptExporter: vi.fn(),
}));

describe("Admin app main path", () => {
  it("sells an unreserved ticket, then verifying its reference returns VALID with the matching NIC", async () => {
    RealApiClient.mockImplementation(() => new FakeApiClient({ trips: [DEMO_TRIP] }));
    RealReceiptExporter.mockImplementation(() => new FakeReceiptExporter());

    render(App);

    await fireEvent.input(screen.getByLabelText("Date"), { target: { value: DEMO_TRIP.service_date } });
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    await userEvent.type(await screen.findByLabelText("Passenger name"), "Ann Perera");
    await userEvent.type(screen.getByLabelText("NIC / passport"), "nic-1");
    await userEvent.click(screen.getByRole("button", { name: /Cash taken/ }));

    const reference = (await screen.findByText(/^Sold — SLR-/)).textContent.replace("Sold — ", "");

    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    await userEvent.type(screen.getByPlaceholderText("SLR-7K3M-92"), reference);
    await userEvent.click(screen.getByRole("button", { name: "Check" }));

    expect(await screen.findByText("Valid")).toBeInTheDocument();
    expect(screen.getByText("nic-1")).toBeInTheDocument();
  });
});
