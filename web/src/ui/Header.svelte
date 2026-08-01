<script>
  // L3: the app header (D26/D27). Skeleton's card/badge-icon presets carry the look; the
  // only hand-written classes are layout (flex/gap), never colour or radius.
  import Icon from "./Icon.svelte";

  let { onhome } = $props();
</script>

<header class="sticky top-0 z-10 border-b border-surface-200-800 preset-tonal-surface backdrop-blur print:hidden">
  <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
    <button
      type="button"
      class="flex items-center gap-2.5 text-left"
      onclick={onhome}
      aria-label="SLR Seat Booking, go to the landing page"
    >
      <span class="badge-icon preset-filled-primary-500">
        <Icon name="train" class="size-5" />
      </span>
      <span class="leading-tight">
        <span class="block font-bold">SLR Seat Booking</span>
        <span class="block text-xs opacity-70">Colombo Fort to Badulla</span>
      </span>
    </button>
  </div>
</header>
