<script>
  // Named-passenger identity (D8): name + NIC/passport, no account. Two-way bound to the
  // parent's passenger object. Mirrors SLR's live named-ticket rule.
  let { passenger = $bindable({ name: "", nic: "" }), disabled = false } = $props();
</script>

<fieldset class="space-y-3" {disabled}>
  <div>
    <label for="pax-name" class="label-text mb-1 block">Passenger name</label>
    <input
      id="pax-name"
      type="text"
      autocomplete="name"
      bind:value={passenger.name}
      placeholder="As printed on the NIC / passport"
      class="input"
    />
  </div>
  <div>
    <label for="pax-nic" class="label-text mb-1 block">NIC / passport</label>
    <input
      id="pax-nic"
      type="text"
      inputmode="text"
      bind:value={passenger.nic}
      placeholder="e.g. 200012345678"
      class="input"
    />
    <p class="mt-1 text-xs opacity-70">Verified at boarding. The ticket is non-transferable.</p>
  </div>
</fieldset>
