<script>
  // L4 composition root: inject the real adapters. This is the only place the concrete
  // fetch/SSE/storage/print adapters are constructed; everything below sees ports only.
  import Header from "../ui/Header.svelte";
  import Footer from "../ui/Footer.svelte";
  import BookingWizard from "../ui/BookingWizard.svelte";
  import { RealApiClient } from "../adapters/api-client.real.js";
  import { RealAvailabilityStream } from "../adapters/availability-stream.real.js";
  import { RealStorage } from "../adapters/storage.real.js";
  import { RealReceiptExporter } from "../adapters/receipt-exporter.real.js";
  import { config } from "./config.js";

  const api = new RealApiClient({ baseUrl: config.apiBaseUrl });
  const stream = new RealAvailabilityStream({ baseUrl: config.apiBaseUrl });
  const storage = new RealStorage();
  const exporter = new RealReceiptExporter();

  let wizard = $state();
</script>

<div class="flex min-h-screen flex-col">
  <Header onhome={() => wizard?.goHome?.()} />
  <main class="flex-1">
    <BookingWizard {api} {stream} {storage} {exporter} bind:this={wizard} />
  </main>
  <Footer />
</div>
