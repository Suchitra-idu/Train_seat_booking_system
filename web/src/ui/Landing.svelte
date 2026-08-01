<script>
  // L3: the landing page (D26). Short by design - no scroll on a normal viewport: hero,
  // one Reserve CTA, three value props.
  import Icon from "./Icon.svelte";

  let { onreserve } = $props();

  const VALUES = [
    { icon: "seat", title: "Pick your seat", body: "A real seat map for every reserved coach, not a queue number." },
    { icon: "map-pin", title: "Pay only for your leg", body: "Fares are priced per journey segment, not the whole route." },
    { icon: "qr", title: "One ticket, verified", body: "A named reference and QR checked at boarding." },
  ];
</script>

<section class="mx-auto flex max-w-5xl flex-col items-center gap-8 px-4 py-12 text-center">
  <span class="badge-icon preset-filled-primary-500 size-16">
    <Icon name="train" class="size-8" />
  </span>

  <div class="space-y-3">
    <h1 class="text-3xl font-bold sm:text-4xl">Book your seat on the Main Line</h1>
    <p class="mx-auto max-w-xl text-base opacity-70">
      Colombo Fort to Badulla. Search a date, pick a train, choose your seat, and pay in
      minutes.
    </p>
  </div>

  <button
    type="button"
    class="btn btn-lg preset-filled-primary-500 gap-2.5 py-4 pr-9 pl-7 text-lg"
    onclick={onreserve}
  >
    <Icon name="search" class="size-5" />
    <span>Reserve a seat</span>
  </button>

  <div class="mt-4 grid w-full gap-4 sm:grid-cols-3">
    {#each VALUES as v (v.title)}
      <div class="card preset-tonal-surface space-y-2 p-5 text-left">
        <span class="badge-icon preset-tonal-primary">
          <Icon name={v.icon} class="size-4" />
        </span>
        <h2 class="font-semibold">{v.title}</h2>
        <p class="text-sm opacity-70">{v.body}</p>
      </div>
    {/each}
  </div>
</section>
