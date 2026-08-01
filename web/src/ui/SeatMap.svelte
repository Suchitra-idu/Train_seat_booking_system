<script>
  import Icon from "./Icon.svelte";
  import Legend from "./Legend.svelte";
  import { classLabel } from "../view-core/seatmap.js";

  let { map, onselect } = $props();

  // Skeleton's preset-* classes are static CSS from the theme, not Tailwind-variant-aware,
  // so hover feedback comes from a plain filter utility layered on top rather than swapping
  // the preset on :hover.
  const STYLES = {
    free: "preset-tonal-success hover:brightness-110 cursor-pointer transition",
    selected: "preset-filled-primary-500 shadow-sm cursor-pointer transition",
    taken: "preset-tonal-surface opacity-60 cursor-not-allowed",
    unreserved: "preset-outlined-warning-500 border-dashed opacity-90 cursor-not-allowed",
    unknown: "preset-tonal-surface opacity-40 cursor-default",
  };

  const coachType = (t) => (t === "UNRESERVED" ? "Unreserved" : "Reserved");
</script>

<div class="space-y-5">
  {#each map.coaches as coach (coach.code)}
    <section class="card preset-tonal-surface p-4">
      <header class="mb-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="badge-icon preset-filled-primary-500 text-sm font-bold">
            {coach.code}
          </span>
          <div class="leading-tight">
            <p class="font-semibold">Coach {coach.code}</p>
            <p class="text-xs opacity-70">{coachType(coach.coachType)} · {classLabel(coach.travelClass)}</p>
          </div>
        </div>
        {#if coach.coachType === "UNRESERVED"}
          <span class="badge preset-tonal-warning text-xs">Seat assigned at counter</span>
        {/if}
      </header>

      <div class="flex flex-wrap gap-2.5" role="group" aria-label={`Coach ${coach.code} seats`}>
        {#each coach.seats as seat (seat.id)}
          <button
            type="button"
            data-seat={seat.id}
            class={`relative flex h-12 w-12 flex-col items-center justify-center rounded-lg border text-sm font-semibold ${STYLES[seat.status]}`}
            aria-label={seat.label}
            aria-pressed={seat.status === "selected"}
            disabled={!seat.selectable}
            onclick={() => seat.selectable && onselect?.(seat.id)}
          >
            {#if seat.status === "selected"}
              <Icon name="check" class="h-4 w-4" />
            {:else if seat.status === "taken"}
              <Icon name="lock" class="h-3.5 w-3.5 opacity-70" />
            {:else}
              <span>{seat.id}</span>
            {/if}
          </button>
        {/each}
      </div>
    </section>
  {/each}

  <Legend />
</div>
