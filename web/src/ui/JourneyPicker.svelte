<script>
  import Icon from "./Icon.svelte";
  import { orderedStations } from "../view-core/stations.js";

  let {
    stations,
    originSeq = $bindable(),
    destSeq = $bindable(),
    travelClass = $bindable("SECOND"),
    onchange,
  } = $props();

  const ordered = $derived(orderedStations(stations));
  const origins = $derived(ordered.filter((s) => s.seq < Math.max(...ordered.map((x) => x.seq))));
  const dests = $derived(ordered.filter((s) => s.seq > originSeq));

  function pickOrigin(v) {
    originSeq = Number(v);
    if (destSeq <= originSeq) {
      const next = ordered.find((s) => s.seq > originSeq);
      if (next) destSeq = next.seq;
    }
    onchange?.();
  }
</script>

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_1fr] lg:items-end">
  <label class="label">
    <span class="label-text">From</span>
    <select class="select" value={originSeq} onchange={(e) => pickOrigin(e.currentTarget.value)}>
      {#each origins as s (s.seq)}<option value={s.seq}>{s.name}</option>{/each}
    </select>
  </label>

  <div class="hidden items-center justify-center pb-2.5 opacity-60 lg:flex">
    <Icon name="arrow" class="h-5 w-5" />
  </div>

  <label class="label">
    <span class="label-text">To</span>
    <select
      class="select"
      value={destSeq}
      onchange={(e) => {
        destSeq = Number(e.currentTarget.value);
        onchange?.();
      }}
    >
      {#each dests as s (s.seq)}<option value={s.seq}>{s.name}</option>{/each}
    </select>
  </label>

  <label class="label">
    <span class="label-text">Class</span>
    <select
      class="select"
      value={travelClass}
      onchange={(e) => {
        travelClass = e.currentTarget.value;
        onchange?.();
      }}
    >
      <option value="FIRST">1st class</option>
      <option value="SECOND">2nd class</option>
      <option value="THIRD">3rd class</option>
    </select>
  </label>
</div>
