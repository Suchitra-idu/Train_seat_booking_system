<script>
  // L3: one passenger row in a group booking (D8, D26). Every seat still gets its own
  // named passenger; the "travelling with" tick is a display-only link to the row
  // directly above it in pick order, not a fare rule and not something the backend knows
  // about, it only shapes the receipt-screen grouping (D24, frontend-only per plan).
  //
  // A linked passenger has no NIC of their own to give (a child riding with a parent, in
  // the plain sense of the word) - the field locks and carries the parent's NIC as the
  // booking identity for that seat, since the backend still requires one passenger_id per
  // booking regardless of the group link.
  let {
    seatLabel,
    passenger,
    parentSeatId = null,
    parentName = "",
    parentNic = "",
    disabled = false,
    oninput,
    onremove,
  } = $props();

  const isChild = $derived(parentSeatId !== null && passenger.childOfSeatId === parentSeatId);
  // A linked row's own `nic` field is never written; the actual booking identity is
  // resolved from the parent chain at submit time (BookingWizard.resolveNic). This is
  // purely what the locked field displays.
  const displayNic = $derived(isChild ? parentNic : passenger.nic);
  const update = (field) => (e) => oninput?.({ [field]: e.currentTarget.value });
  const toggleChild = (e) => oninput?.({ childOfSeatId: e.currentTarget.checked ? parentSeatId : null });
</script>

<div class="card preset-tonal-surface space-y-3 p-4">
  <div class="flex items-center justify-between">
    <span class="badge preset-tonal-primary text-xs">Seat {seatLabel}</span>
    {#if onremove}
      <button type="button" class="text-xs opacity-60 hover:opacity-100" onclick={onremove}>
        Remove
      </button>
    {/if}
  </div>

  <fieldset class="grid gap-3 sm:grid-cols-2" {disabled}>
    <label class="label">
      <span class="label-text">Passenger name</span>
      <input
        type="text"
        autocomplete="name"
        class="input"
        value={passenger.name}
        oninput={update("name")}
        placeholder="As printed on the NIC / passport"
      />
    </label>
    <label class="label">
      <span class="label-text">NIC / passport</span>
      <input
        type="text"
        inputmode="text"
        class="input"
        value={displayNic}
        oninput={update("nic")}
        disabled={disabled || isChild}
        placeholder={isChild ? "Travelling under the linked passenger's NIC" : "e.g. 200012345678"}
      />
    </label>
  </fieldset>

  {#if parentSeatId !== null}
    <label class="flex items-center gap-2 text-sm">
      <input type="checkbox" class="checkbox" checked={isChild} onchange={toggleChild} {disabled} />
      <span>Travelling with {parentName || "the passenger above"}</span>
    </label>
  {/if}
</div>
