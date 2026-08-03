<script>
  // L3: the counter app's header (D21, D27), doubling as the Sell/Verify tab switcher —
  // there are only two screens, so a router is overkill (mirrors D26's reasoning for the
  // traveller app's step reducer instead of one).
  import Icon from "./Icon.svelte";

  let { tab, ontab } = $props();
</script>

<header class="sticky top-0 z-10 border-b border-surface-200-800 preset-tonal-surface backdrop-blur print:hidden">
  <div class="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 px-4 py-3">
    <span class="flex items-center gap-2.5">
      <span class="badge-icon preset-filled-primary-500">
        <Icon name="train" class="size-5" />
      </span>
      <span class="leading-tight">
        <span class="block font-bold">SLR Ticket Counter</span>
        <span class="block text-xs opacity-70">Sell &amp; verify</span>
      </span>
    </span>

    <div class="btn-group preset-outlined-primary-500">
      <button
        type="button"
        class="btn btn-sm"
        aria-pressed={tab === "sell"}
        class:preset-filled-primary-500={tab === "sell"}
        onclick={() => ontab?.("sell")}
      >
        <Icon name="banknote" class="size-4" />
        Sell
      </button>
      <button
        type="button"
        class="btn btn-sm"
        aria-pressed={tab === "verify"}
        class:preset-filled-primary-500={tab === "verify"}
        onclick={() => ontab?.("verify")}
      >
        <Icon name="shield-check" class="size-4" />
        Verify
      </button>
    </div>
  </div>
</header>
