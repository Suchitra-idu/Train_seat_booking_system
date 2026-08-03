<script>
  // L3: verify any ticket, bought in the app or sold at this counter (D21, D24). Reference
  // entry only, no camera scanning, a QR just encodes this same reference so typing it in
  // is a strict superset of what a scanner would give the inspector.
  import Icon from "./Icon.svelte";
  import Ticket from "./Ticket.svelte";
  import { NotFoundError } from "../ports/errors.js";
  import { verifyView, notFoundView } from "../view-core/verify.js";

  let { api } = $props();

  let reference = $state("");
  let result = $state(null);

  const TONE_ICON = { success: "circle-check", warning: "lock", error: "alert" };

  async function check(e) {
    e.preventDefault();
    if (!reference.trim()) return;
    try {
      const out = await api.verify(reference.trim());
      result = verifyView(out);
    } catch (e2) {
      if (e2 instanceof NotFoundError) {
        result = notFoundView();
      } else {
        throw e2;
      }
    }
  }
</script>

<div class="mx-auto max-w-2xl space-y-4">
  <form class="card preset-tonal-surface flex flex-wrap items-end gap-4 p-5" onsubmit={check}>
    <label class="label flex-1">
      <span class="label-text">Reference</span>
      <input type="text" class="input font-mono" bind:value={reference} placeholder="SLR-7K3M-92" />
    </label>
    <button type="submit" class="btn preset-filled-primary-500" disabled={!reference.trim()}>
      <Icon name="shield-check" class="size-4" />
      Check
    </button>
  </form>

  {#if result}
    <div
      class="card flex items-center gap-3 p-4"
      class:preset-tonal-success={result.tone === "success"}
      class:preset-tonal-warning={result.tone === "warning"}
      class:preset-tonal-error={result.tone === "error"}
      role="status"
    >
      <span
        class="badge-icon"
        class:preset-filled-success-500={result.tone === "success"}
        class:preset-filled-warning-500={result.tone === "warning"}
        class:preset-filled-error-500={result.tone === "error"}
      >
        <Icon name={TONE_ICON[result.tone]} class="size-5" />
      </span>
      <p class="font-semibold">{result.label}</p>
    </div>

    {#if result.ticket}
      <Ticket view={result.ticket} />
    {/if}
  {/if}
</div>
