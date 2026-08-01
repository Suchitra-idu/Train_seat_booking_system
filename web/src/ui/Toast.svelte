<script>
  import Icon from "./Icon.svelte";
  let { kind = "info", message, onclose } = $props();
  const preset = {
    error: "preset-tonal-error",
    success: "preset-tonal-success",
    info: "preset-tonal-primary",
  };
</script>

{#if message}
  <div class={`card flex items-start gap-3 p-3 text-sm ${preset[kind]}`} role="status">
    <Icon name={kind === "success" ? "check" : "alert"} class="mt-0.5 h-4 w-4 shrink-0" />
    <p class="flex-1">{message}</p>
    {#if onclose}
      <button type="button" class="text-xs font-medium underline-offset-2 hover:underline" onclick={onclose}>
        Dismiss
      </button>
    {/if}
  </div>
{/if}
