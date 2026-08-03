<script>
  // L4 composition root: inject the real adapters. This is the only place the concrete
  // fetch/print adapters are constructed; everything below sees ports only (D21).
  import Header from "../ui/Header.svelte";
  import Footer from "../ui/Footer.svelte";
  import SellForm from "../ui/SellForm.svelte";
  import VerifyForm from "../ui/VerifyForm.svelte";
  import { RealApiClient } from "../adapters/api-client.real.js";
  import { RealReceiptExporter } from "../adapters/receipt-exporter.real.js";
  import { config } from "./config.js";

  const api = new RealApiClient({ baseUrl: config.apiBaseUrl, counterKey: config.counterKey });
  const exporter = new RealReceiptExporter();

  let tab = $state("sell");
</script>

<div class="flex min-h-screen flex-col">
  <Header {tab} ontab={(t) => (tab = t)} />
  <main class="flex-1 px-4 py-6">
    {#if tab === "sell"}
      <SellForm {api} {exporter} />
    {:else}
      <VerifyForm {api} />
    {/if}
  </main>
  <Footer />
</div>
