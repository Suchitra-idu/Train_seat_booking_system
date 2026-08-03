<script>
  // L3: one ticket, shared by the sell result and the verify result (D21, D24). Shows the
  // passenger's NIC, unlike the traveller app's TicketCard, this is the screen where it's
  // actually compared against the ID in the passenger's hand.
  import Icon from "./Icon.svelte";
  import { qrMatrix } from "../view-core/qr.js";
  import { qrFilename } from "../ports/receipt-exporter.js";

  let { view, exporter = null } = $props();

  const matrix = $derived(qrMatrix(view.qrPayload));
</script>

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
    <div><dt class="opacity-70">Status</dt><dd class="font-medium">{view.status}</dd></div>
    <div><dt class="opacity-70">Passenger</dt><dd class="font-medium">{view.passengerName}</dd></div>
    <div><dt class="opacity-70">NIC / passport</dt><dd class="font-mono font-medium">{view.passengerId}</dd></div>
    <div><dt class="opacity-70">Class</dt><dd class="font-medium">{view.travelClass}</dd></div>
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

  {#if exporter}
    <div class="flex flex-wrap gap-3 print:hidden">
      <button type="button" class="btn btn-sm preset-outlined-primary-500" onclick={() => exporter.print()}>
        <Icon name="printer" class="size-4" />
        Print
      </button>
      <button
        type="button"
        class="btn btn-sm preset-outlined-primary-500"
        onclick={() => exporter.downloadQrPng(matrix, qrFilename(view.reference))}
      >
        <Icon name="qr" class="size-4" />
        Download QR
      </button>
    </div>
  {/if}
</div>
