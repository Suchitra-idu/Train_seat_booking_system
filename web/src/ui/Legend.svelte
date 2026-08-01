<script>
  import Icon from "./Icon.svelte";
  // Seat states never rely on colour alone (WCAG): each carries a glyph and a word.
  const items = [
    { key: "free", label: "Available", cls: "preset-tonal-success" },
    { key: "selected", label: "Selected", cls: "preset-filled-primary-500", icon: "check" },
    { key: "taken", label: "Booked", cls: "preset-tonal-surface", icon: "lock" },
    { key: "unreserved", label: "Unreserved", cls: "preset-outlined-warning-500 border-dashed" },
  ];
</script>

<ul class="flex flex-wrap gap-x-5 gap-y-2 text-sm opacity-80">
  {#each items as it (it.key)}
    <li class="flex items-center gap-2">
      <span class={`badge-icon ${it.cls}`}>
        {#if it.icon}<Icon name={it.icon} class="h-3.5 w-3.5" />{/if}
      </span>
      {it.label}
    </li>
  {/each}
</ul>
