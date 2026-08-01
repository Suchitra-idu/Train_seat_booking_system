<script>
  // L3: one ticket (D24). Renders the QR as inline SVG from the pure matrix
  // (view-core/qr.js); Print/Download go through the ReceiptExporter port, never
  // window.print or canvas directly. `linkedToName` is the frontend-only "travelling
  // with" grouping (checkout-session display only, nothing the backend stores).
  import Icon from "./Icon.svelte";
  import { receiptView } from "../view-core/receipt.js";
  import { qrMatrix } from "../view-core/qr.js";
  import { qrFilename } from "../ports/receipt-exporter.js";

  let { receipt, exporter, linkedToName = null } = $props();

  const view = $derived(receiptView(receipt));
  const matrix = $derived(qrMatrix(view.qrPayload));
  const wrapperClass = $derived(
    linkedToName ? "ml-6 border-l-2 border-primary-500/40 pl-4" : "",
  );
</script>

<div class={wrapperClass}>
  {#if linkedToName}
    <p class="mb-2 flex items-center gap-1.5 text-xs opacity-70">
      <Icon name="arrow-right" class="size-3 rotate-90" />
      Travelling with {linkedToName}
    </p>
  {/if}

  <div id={`ticket-${view.reference}`} class="receipt-card card preset-tonal-surface space-y-4 p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-sm opacity-70">{view.trainNo} &middot; {view.trainName}</p>
        <p class="text-lg font-bold">{view.origin} &rarr; {view.dest}</p>
        <p class="text-sm opacity-70">{view.serviceDate} &middot; {view.depart} &rarr; {view.arrive}</p>
      </div>
      <div class="shrink-0 rounded-lg bg-white p-1.5">
        <svg viewBox={`0 0 ${matrix.size} ${matrix.size}`} class="size-24" role="img" aria-label={`QR code for reference ${view.reference}`}>
          {#each Array(matrix.size) as _, row (row)}
            {#each Array(matrix.size) as _2, col (col)}
              {#if matrix.isDark(row, col)}
                <rect x={col} y={row} width="1" height="1" fill="black" />
              {/if}
            {/each}
          {/each}
        </svg>
      </div>
    </div>

    <hr class="border-surface-200-800" />

    <dl class="grid grid-cols-2 gap-3 text-sm">
      <div><dt class="opacity-70">Reference</dt><dd class="font-mono font-bold">{view.reference}</dd></div>
      <div><dt class="opacity-70">Passenger</dt><dd class="font-medium">{view.passengerName}</dd></div>
      {#if view.isStanding}
        <div class="col-span-2">
          <dt class="opacity-70">Standing</dt>
          <dd class="font-medium">
            Sit on seat {view.standing.seatLabel} after {view.standing.afterStation}
          </dd>
        </div>
      {:else}
        <div><dt class="opacity-70">Coach / Seat</dt><dd class="font-medium">{view.coach} / {view.seatLabel}</dd></div>
      {/if}
      <div><dt class="opacity-70">Fare</dt><dd class="font-bold">{view.fare}</dd></div>
    </dl>

    <div class="flex flex-wrap gap-3 print:hidden">
      <button type="button" class="btn btn-sm preset-outlined-primary-500" onclick={() => exporter?.print()}>
        <Icon name="printer" class="size-4" />
        Print / Save as PDF
      </button>
      <button
        type="button"
        class="btn btn-sm preset-outlined-primary-500"
        onclick={() => exporter?.downloadQrPng(matrix, qrFilename(view.reference))}
      >
        <Icon name="download" class="size-4" />
        Download QR
      </button>
    </div>
  </div>
</div>
