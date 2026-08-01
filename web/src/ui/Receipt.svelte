<script>
  // L3: the receipt screen for a group booking (D24, D26). `tickets` is one entry per
  // seat: { seatId, childOfSeatId, receipt }. The "travelling with" link is resolved here
  // by walking back to the parent ticket's passenger name - a checkout-session display
  // concern only, nothing persisted on the backend (see the D24 grouping decision).
  import Icon from "./Icon.svelte";
  import TicketCard from "./TicketCard.svelte";

  let { tickets, exporter, onbookanother } = $props();

  const linkedCount = $derived(tickets.filter((t) => t.childOfSeatId !== null).length);
  const summary = $derived(
    tickets.length === 1
      ? "1 ticket booked"
      : linkedCount > 0
        ? `${tickets.length} tickets booked as a group (${linkedCount} linked)`
        : `${tickets.length} tickets booked`,
  );

  function nameOf(seatId) {
    return tickets.find((t) => t.seatId === seatId)?.receipt.passenger_name ?? null;
  }
</script>

<div class="mx-auto max-w-md space-y-4 print:max-w-full">
  <div class="card preset-tonal-success flex items-center gap-3 p-4 print:hidden" role="status">
    <span class="badge-icon preset-filled-success-500">
      <Icon name="check" class="size-5" />
    </span>
    <p class="font-semibold">{summary}</p>
  </div>

  <div class="space-y-4">
    {#each tickets as ticket (ticket.seatId)}
      <TicketCard
        receipt={ticket.receipt}
        {exporter}
        linkedToName={ticket.childOfSeatId !== null ? nameOf(ticket.childOfSeatId) : null}
      />
    {/each}
  </div>

  <div class="flex justify-end print:hidden">
    <button type="button" class="btn preset-filled-primary-500" onclick={onbookanother}>
      Book more seats
    </button>
  </div>
</div>
