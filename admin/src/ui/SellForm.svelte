<script>
  // L3: sell an unreserved ticket (D21, D23). Search finds the trip/leg, a class pick and
  // cash-taken finish it in one call, the backend seats or stands the passenger and charges
  // in the same transaction, there's no separate "confirm" step here unlike the app.
  import Icon from "./Icon.svelte";
  import Ticket from "./Ticket.svelte";
  import { STATIONS } from "../view-core/route.js";
  import { isoDate } from "../view-core/time.js";
  import { receiptView } from "../view-core/receipt.js";
  import { TRAVEL_CLASSES, sellReady, sellRequest } from "../view-core/sell.js";

  let { api, exporter } = $props();

  const today = isoDate();
  let originCode = $state(STATIONS[0].code);
  let destCode = $state(STATIONS[STATIONS.length - 1].code);
  let serviceDate = $state(today);
  let trains = $state([]);
  let selectedTripId = $state("");
  let travelClass = $state(TRAVEL_CLASSES[1]);
  let passengerId = $state("");
  let passengerName = $state("");
  let receipt = $state(null);
  let error = $state("");

  const train = $derived(trains.find((t) => t.trip_id === selectedTripId) ?? null);
  const ready = $derived(sellReady({ train, travelClass, passengerId, passengerName }));
  const view = $derived(receipt ? receiptView(receipt) : null);

  async function search(e) {
    e.preventDefault();
    error = "";
    trains = await api.searchTrains({ originCode, destCode, serviceDate });
    selectedTripId = trains[0]?.trip_id ?? "";
  }

  async function sell() {
    if (!ready) return;
    error = "";
    try {
      receipt = await api.sell(sellRequest({ train, travelClass, passengerId, passengerName }));
    } catch (e) {
      error = e.message;
    }
  }

  function newSale() {
    receipt = null;
    passengerId = "";
    passengerName = "";
    error = "";
  }
</script>

<div class="mx-auto max-w-2xl space-y-4">
  {#if view}
    <div class="card preset-tonal-success flex items-center gap-3 p-4" role="status">
      <span class="badge-icon preset-filled-success-500"><Icon name="check" class="size-5" /></span>
      <p class="font-semibold">Sold — {view.reference}</p>
    </div>
    <Ticket {view} {exporter} />
    <div class="flex justify-end">
      <button type="button" class="btn preset-filled-primary-500" onclick={newSale}>
        <Icon name="banknote" class="size-4" />
        Next sale
      </button>
    </div>
  {:else}
    <form
      class="card preset-tonal-surface grid gap-x-8 gap-y-4 p-5 sm:grid-cols-[1fr_auto_1fr_auto_auto] sm:items-end"
      onsubmit={search}
    >
      <label class="label">
        <span class="label-text">From</span>
        <select class="select pr-8 pl-3" bind:value={originCode}>
          {#each STATIONS as s (s.code)}<option value={s.code}>{s.name}</option>{/each}
        </select>
      </label>
      <div class="hidden items-center justify-center pb-2.5 opacity-60 sm:flex">
        <Icon name="arrow-right" class="size-5" />
      </div>
      <label class="label">
        <span class="label-text">To</span>
        <select class="select pr-8 pl-3" bind:value={destCode}>
          {#each STATIONS as s (s.code)}<option value={s.code}>{s.name}</option>{/each}
        </select>
      </label>
      <label class="label">
        <span class="label-text">Date</span>
        <input type="date" class="input" min={today} bind:value={serviceDate} />
      </label>
      <button type="submit" class="btn preset-filled-primary-500" disabled={originCode === destCode}>
        <Icon name="search" class="size-4" />
        Search
      </button>
    </form>

    {#if trains.length > 0}
      <div class="card preset-tonal-surface space-y-4 p-5">
        <label class="label">
          <span class="label-text">Train</span>
          <select class="select pr-8 pl-3" bind:value={selectedTripId}>
            {#each trains as t (t.trip_id)}
              <option value={t.trip_id}>{t.train_no} {t.train_name} — {t.depart} → {t.arrive}</option>
            {/each}
          </select>
        </label>

        <label class="label">
          <span class="label-text">Class</span>
          <select class="select pr-8 pl-3" bind:value={travelClass}>
            {#each TRAVEL_CLASSES as c (c)}<option value={c}>{c}</option>{/each}
          </select>
        </label>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="label">
            <span class="label-text">Passenger name</span>
            <input type="text" class="input" bind:value={passengerName} placeholder="As printed on the NIC / passport" />
          </label>
          <label class="label">
            <span class="label-text">NIC / passport</span>
            <input type="text" class="input" bind:value={passengerId} placeholder="e.g. 200012345678" />
          </label>
        </div>

        {#if error}
          <p class="text-sm text-error-500" role="alert">{error}</p>
        {/if}

        <div class="flex justify-end">
          <button type="button" class="btn preset-filled-primary-500" disabled={!ready} onclick={sell}>
            <Icon name="banknote" class="size-4" />
            Cash taken — sell
          </button>
        </div>
      </div>
    {:else if selectedTripId === "" && trains.length === 0}
      <p class="text-center text-sm opacity-60">Search a journey to see trains running that day.</p>
    {/if}
  {/if}
</div>
