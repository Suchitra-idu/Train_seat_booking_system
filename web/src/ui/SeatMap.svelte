<script>
  // L3: the seat map, one coach at a time with a switcher (D25/D26). The seat-cell grid
  // itself is hand-built (Skeleton has no seat-map primitive, PHASES.md P6c); seat status
  // still renders through Skeleton's preset-* classes so the theme owns the colours.
  import Icon from "./Icon.svelte";
  import Legend from "./Legend.svelte";
  import { classLabel } from "../view-core/seatmap.js";

  // A booking session can hold several seats at once (a group), so a click toggles
  // membership rather than replacing a single selection.
  let { map, ontoggle } = $props();

  const STYLES = {
    free: "preset-tonal-success hover:brightness-110 cursor-pointer transition",
    selected: "preset-filled-primary-500 shadow-sm cursor-pointer transition",
    taken: "preset-tonal-surface opacity-60 cursor-not-allowed",
    unreserved: "preset-outlined-warning-500 border-dashed opacity-90 cursor-not-allowed",
    unknown: "preset-tonal-surface opacity-40 cursor-default",
  };

  const coachType = (t) => (t === "UNRESERVED" ? "Unreserved" : "Reserved");

  // Local selection with a reactive fallback: it stays put across re-renders of the same
  // map (live availability deltas), but snaps back to the first coach if the coach set
  // itself changes (a different train).
  let activeCode = $state(undefined);
  $effect(() => {
    if (!map.coaches.some((c) => c.code === activeCode)) activeCode = map.coaches[0]?.code;
  });
  const active = $derived(map.coaches.find((c) => c.code === activeCode) || map.coaches[0]);

  function seatButton(seat) {
    return { class: `relative flex size-11 flex-col items-center justify-center rounded-lg border text-sm font-semibold ${STYLES[seat.status]}` };
  }
</script>

<div class="space-y-4">
  <div class="card preset-tonal-surface flex flex-wrap items-center justify-between gap-3 p-3">
    <div class="btn-group preset-outlined-surface-200-800 flex-wrap p-1 text-sm">
      {#each map.coaches as coach (coach.code)}
        <button
          type="button"
          class={`btn btn-sm ${coach.code === activeCode ? "preset-filled-primary-500" : ""}`}
          onclick={() => (activeCode = coach.code)}
        >
          Coach {coach.code}
        </button>
      {/each}
    </div>
    {#if active}
      <div class="text-right text-sm">
        <p class="font-semibold">{coachType(active.coachType)} &middot; {classLabel(active.travelClass)}</p>
        {#if active.coachType === "UNRESERVED"}
          <p class="text-xs opacity-70">Seat assigned at the counter</p>
        {:else}
          <p class="text-xs opacity-70">{active.reservedFreeCount} of {active.reservedTotal} free</p>
        {/if}
      </div>
    {/if}
  </div>

  {#if active}
    <div class="card preset-tonal-surface p-4">
      <div class="mx-auto flex max-w-xs flex-col gap-2" role="group" aria-label={`Coach ${active.code} seats`}>
        {#each active.rows as row (row.row)}
          <div class="flex items-center justify-center gap-3">
            <div class="flex gap-2">
              {#each row.left as seat (seat.id)}
                <button
                  type="button"
                  data-seat={seat.id}
                  {...seatButton(seat)}
                  aria-label={seat.label}
                  aria-pressed={seat.status === "selected"}
                  disabled={!seat.selectable}
                  onclick={() => seat.selectable && ontoggle?.(seat.id)}
                >
                  {#if seat.status === "selected"}
                    <Icon name="check" class="size-4" />
                  {:else if seat.status === "taken"}
                    <Icon name="lock" class="size-3.5 opacity-70" />
                  {:else}
                    {seat.column}
                  {/if}
                </button>
              {/each}
            </div>

            <span class="w-6 text-center text-xs font-medium opacity-60">{row.row}</span>

            {#if row.right.length > 0}
              <div class="flex gap-2">
                {#each row.right as seat (seat.id)}
                  <button
                    type="button"
                    data-seat={seat.id}
                    {...seatButton(seat)}
                    aria-label={seat.label}
                    aria-pressed={seat.status === "selected"}
                    disabled={!seat.selectable}
                    onclick={() => seat.selectable && ontoggle?.(seat.id)}
                  >
                    {#if seat.status === "selected"}
                      <Icon name="check" class="size-4" />
                    {:else if seat.status === "taken"}
                      <Icon name="lock" class="size-3.5 opacity-70" />
                    {:else}
                      {seat.column}
                    {/if}
                  </button>
                {/each}
              </div>
            {/if}
          </div>
          {#if row.exitAfter}
            <div class="flex items-center gap-2 py-1 text-xs opacity-50">
              <Icon name="arrow-right" class="size-3" />
              <span>Exit row</span>
              <hr class="flex-1 border-surface-200-800" />
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}

  <Legend />
</div>
