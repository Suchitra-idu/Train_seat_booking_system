<script>
  // L3: one card per train (D26). The empty state names the reason instead of showing
  // nothing, since "no trains today" and "route doesn't exist" read very differently.
  import Icon from "./Icon.svelte";
  import { trainRows } from "../view-core/trains.js";
  import { formatMoney } from "../view-core/money.js";

  let { options, journey, onback, onselect } = $props();
  // Zip each display row back to its raw TrainOptionOut, since onselect needs the wire
  // fields (trip_id, origin_seq, dest_seq) the view-model doesn't carry.
  const entries = $derived(trainRows(options).map((row, i) => ({ row, option: options[i] })));
</script>

<div class="space-y-4">
  <button type="button" class="flex items-center gap-1 text-sm font-medium opacity-70 hover:opacity-100" onclick={onback}>
    <Icon name="chevron-left" class="size-4" />
    Change search
  </button>

  {#if entries.length === 0}
    <div class="card preset-tonal-surface p-10 text-center">
      <Icon name="alert" class="mx-auto mb-2 size-6 opacity-60" />
      <p class="font-medium">No trains run this route on {journey?.serviceDate}.</p>
      <p class="mt-1 text-sm opacity-70">Try a different date.</p>
    </div>
  {:else}
    {#each entries as { row, option } (row.tripId)}
      <div class="card preset-tonal-surface flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-4">
          <span class="badge-icon preset-filled-primary-500">
            <Icon name="train" class="size-5" />
          </span>
          <div>
            <p class="font-semibold">{row.trainNo} &middot; {row.trainName}</p>
            <p class="text-sm opacity-70">
              {row.depart} &rarr; {row.arrive} &middot; {row.duration}
            </p>
            <div class="mt-1 flex flex-wrap gap-1.5">
              {#each row.classes as c (c.travelClass)}
                <span class="badge preset-tonal-surface text-xs">
                  {c.label}: {c.freeSeats} free
                </span>
              {/each}
            </div>
          </div>
        </div>

        <div class="flex items-center gap-4 sm:flex-col sm:items-end sm:gap-2">
          <div class="text-right">
            <p class="text-xs opacity-70">from</p>
            <p class="text-lg font-bold">{formatMoney(row.fromFare)}</p>
          </div>
          <button
            type="button"
            class="btn preset-filled-primary-500"
            disabled={row.soldOut}
            onclick={() => onselect?.(option)}
          >
            {row.soldOut ? "Sold out" : "Select"}
          </button>
        </div>
      </div>
    {/each}
  {/if}
</div>
