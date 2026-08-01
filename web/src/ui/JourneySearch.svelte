<script>
  // L3: date + From/To (D22, D26). Client-side validation mirrors the server's leg rules
  // (no reversed/identical stations, no date in the past) so a bad search never round-trips.
  import Icon from "./Icon.svelte";
  import { STATIONS } from "../view-core/route.js";
  import { isoDate } from "../view-core/time.js";

  let { onsearch } = $props();

  const today = isoDate();
  let originCode = $state(STATIONS[0].code);
  let destCode = $state(STATIONS[STATIONS.length - 1].code);
  let serviceDate = $state(today);

  const invalid = $derived(!originCode || !destCode || originCode === destCode || !serviceDate);

  function submit(e) {
    e.preventDefault();
    if (invalid) return;
    onsearch?.({ originCode, destCode, serviceDate });
  }
</script>

<form class="card preset-tonal-surface grid gap-4 p-5 sm:grid-cols-[1fr_auto_1fr_auto_auto] sm:items-end" onsubmit={submit}>
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

  <button type="submit" class="btn preset-filled-primary-500" disabled={invalid}>
    <Icon name="search" class="size-4" />
    Search
  </button>

  {#if originCode === destCode}
    <p class="text-sm text-error-500 sm:col-span-5" role="alert">
      Choose two different stations.
    </p>
  {/if}
</form>
