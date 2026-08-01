<script>
  // L4 composition root: inject the real adapters into the UI. This is the only place the
  // concrete fetch/SSE/storage adapters are constructed; everything below sees ports only.
  import BookingFlow from "../ui/BookingFlow.svelte";
  import Icon from "../ui/Icon.svelte";
  import { RealApiClient } from "../adapters/api-client.real.js";
  import { RealAvailabilityStream } from "../adapters/availability-stream.real.js";
  import { RealStorage } from "../adapters/storage.real.js";
  import { config } from "./config.js";

  const api = new RealApiClient({ baseUrl: config.apiBaseUrl });
  const stream = new RealAvailabilityStream({ baseUrl: config.apiBaseUrl });
  const storage = new RealStorage();
</script>

<div class="min-h-screen">
  <header class="sticky top-0 z-10 border-b border-surface-200-800 preset-tonal-surface backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
      <div class="flex items-center gap-2.5">
        <span class="badge-icon preset-filled-primary-500">
          <Icon name="train" class="h-5 w-5" />
        </span>
        <div class="leading-tight">
          <p class="font-bold">SLR Seat Booking</p>
          <p class="text-xs opacity-70">Colombo Fort to Badulla</p>
        </div>
      </div>
    </div>
  </header>

  <main>
    <BookingFlow {api} {stream} {storage} routeCode={config.routeCode} serviceDate={config.serviceDate} />
  </main>
</div>
