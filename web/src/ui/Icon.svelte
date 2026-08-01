<script>
  // Tiny inline icon set - keeps status cues non-colour-only (a11y) with no icon dependency.
  let { name, class: cls = "h-4 w-4" } = $props();
  const paths = {
    check: "M20 6 9 17l-5-5",
    lock: "M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z",
    train:
      "M8 3h8a4 4 0 0 1 4 4v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a4 4 0 0 1 4-4zM4 11h16M9 17l-2 4M15 17l2 4M8.5 7.5h7",
    arrow: "M5 12h14M13 6l6 6-6 6",
    clock: "M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
    alert: "M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
    ticket:
      "M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 1 0 4H5a2 2 0 0 1 0-4 2 2 0 0 0 0-4zM12 6v12",
    seat: "M4 18v-6a2 2 0 0 1 2-2h1V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v10M7 18h12M4 18h2",
  };
</script>

<svg
  class={cls}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
>
  <path d={paths[name]} />
</svg>
