<script>
  import JourneyPicker from "./JourneyPicker.svelte";
  import SeatMap from "./SeatMap.svelte";
  import PassengerForm from "./PassengerForm.svelte";
  import Toast from "./Toast.svelte";
  import Icon from "./Icon.svelte";

  import { buildSeatMap } from "../view-core/seatmap.js";
  import { legLabel, legDistanceKm } from "../view-core/stations.js";
  import { formatMoney, formatKm } from "../view-core/money.js";
  import { bookingReducer, initialBookingState, isBusy } from "../view-core/booking.js";
  import { STORAGE_KEYS } from "../ports/storage.js";
  import { ConflictError, RateLimitError, PaymentError, ValidationError } from "../ports/errors.js";

  let {
    api,
    stream = null,
    storage = null,
    routeCode = "CMB-BAD",
    serviceDate = "2026-08-12",
  } = $props();

  let trip = $state(null);
  let loading = $state(true);
  let mode = $state("reserved"); // reserved | unreserved

  let originSeq = $state(0);
  let destSeq = $state(5);
  let travelClass = $state("SECOND");

  let availability = $state(null);
  let selectedSeatId = $state(null);
  let quote = $state(null);
  let bookState = $state(initialBookingState);
  let unreservedResult = $state(null);

  let passenger = $state({ name: "", nic: "" });
  let toast = $state(null);

  const leg = $derived({ originSeq, destSeq });
  const seatMap = $derived(buildSeatMap({ trip, availability, selectedSeatId }));
  const soldOut = $derived(!!availability && seatMap.reservedFreeCount === 0);
  const distanceKm = $derived(trip ? legDistanceKm(trip.stations, leg) : 0);
  const passengerId = $derived(passenger.nic.trim());
  const passengerReady = $derived(passenger.name.trim().length > 0 && passengerId.length > 0);
  const busy = $derived(isBusy(bookState));
  const classLabel = $derived(
    travelClass === "FIRST" ? "1st class" : travelClass === "SECOND" ? "2nd class" : "3rd class",
  );

  const dispatch = (action) => (bookState = bookingReducer(bookState, action));
  const notify = (kind, message) => (toast = { kind, message });
  const messageFor = (err, fallback) => err?.detail || err?.message || fallback;

  $effect(() => {
    if (storage) {
      const saved = storage.get(STORAGE_KEYS.PASSENGER);
      if (saved?.nic) passenger = saved;
    }
    load();
  });

  async function load() {
    loading = true;
    try {
      const trips = await api.listTrips({ routeCode, serviceDate });
      trip = trips[0] || null;
      if (trip) {
        await refreshAvailability();
        stream?.subscribe(trip.trip_id, { onDelta: () => refreshAvailability() });
      }
    } catch (err) {
      notify("error", messageFor(err, "Could not load the journey."));
    } finally {
      loading = false;
    }
  }

  async function refreshAvailability() {
    if (!trip || originSeq >= destSeq) return;
    try {
      availability = await api.availability(trip.trip_id, { originSeq, destSeq });
      const stillFree = seatMap.coaches
        .flatMap((c) => c.seats)
        .some((s) => s.id === selectedSeatId && s.selectable);
      if (selectedSeatId && !stillFree && bookState.status !== "confirmed") {
        selectedSeatId = null;
      }
    } catch (err) {
      notify("error", messageFor(err, "Could not load availability."));
    }
  }

  function onLegChange() {
    selectedSeatId = null;
    quote = null;
    unreservedResult = null;
    dispatch({ type: "RESET" });
    refreshAvailability();
  }

  async function selectSeat(seatId) {
    if (busy || bookState.status === "confirmed") return;
    selectedSeatId = seatId;
    try {
      quote = await api.quote({ tripId: trip.trip_id, originSeq, destSeq, travelClass });
    } catch (err) {
      notify("error", messageFor(err, "Could not price that seat."));
    }
  }

  const persistPassenger = () => storage?.set(STORAGE_KEYS.PASSENGER, passenger);

  // One user action: reserve the seat and pay. The hold is an internal step (it stops
  // someone else taking the seat while payment is taken), never surfaced to the traveller.
  async function reserveAndPay() {
    if (!selectedSeatId || !passengerReady || busy) return;
    persistPassenger();

    dispatch({ type: "HOLD_REQUESTED" });
    let booking;
    try {
      booking = await api.hold(
        { tripId: trip.trip_id, seatId: selectedSeatId, originSeq, destSeq, passengerId, travelClass },
        { idempotencyKey: `hold:${selectedSeatId}:${originSeq}-${destSeq}:${passengerId}` },
      );
      dispatch({ type: "HOLD_SUCCEEDED", booking });
    } catch (err) {
      handleReserveError(err);
      return;
    }

    dispatch({ type: "CONFIRM_REQUESTED" });
    try {
      const confirmed = await api.confirm(booking.booking_id);
      dispatch({ type: "CONFIRM_SUCCEEDED", booking: confirmed });
    } catch (err) {
      try {
        await api.cancel(booking.booking_id); // release so the seat is not stuck
      } catch {
        /* best effort */
      }
      dispatch({ type: "FAILED", kind: err instanceof PaymentError ? "payment" : "error", message: err?.message });
      notify("error", messageFor(err, "Payment could not be completed. Please try again."));
      await refreshAvailability();
    }
  }

  function handleReserveError(err) {
    if (err instanceof ConflictError) {
      dispatch({ type: "HOLD_CONFLICT", message: messageFor(err, "That seat was just taken.") });
      notify("error", "That seat was just taken. Please pick another.");
      selectedSeatId = null;
      refreshAvailability();
    } else if (err instanceof RateLimitError) {
      dispatch({ type: "FAILED", kind: "rate", message: err.message });
      notify("error", messageFor(err, "Too many requests. Please slow down."));
    } else if (err instanceof ValidationError) {
      dispatch({ type: "FAILED", kind: "validation", message: err.message });
      notify("error", messageFor(err, "That request is not valid."));
    } else {
      dispatch({ type: "FAILED", message: messageFor(err, "Could not reserve the seat.") });
      notify("error", messageFor(err, "Could not reserve the seat."));
    }
  }

  function bookAnother() {
    dispatch({ type: "RESET" });
    selectedSeatId = null;
    quote = null;
    toast = null;
    refreshAvailability();
  }

  async function joinWaitlist() {
    if (!passengerReady) {
      notify("error", "Add your name and NIC to join the waitlist.");
      return;
    }
    persistPassenger();
    try {
      await api.joinWaitlist({ tripId: trip.trip_id, originSeq, destSeq, passengerId, travelClass });
      notify("success", "You are on the waitlist. We will assign a seat as soon as one frees.");
    } catch (err) {
      notify("error", messageFor(err, "Could not join the waitlist."));
    }
  }

  async function bookUnreserved() {
    if (!passengerReady) {
      notify("error", "Add your name and NIC to book.");
      return;
    }
    persistPassenger();
    try {
      unreservedResult = await api.unreserved(
        { tripId: trip.trip_id, originSeq, destSeq, passengerId, travelClass },
        { idempotencyKey: `unres:${originSeq}-${destSeq}:${passengerId}` },
      );
      notify("success", `Booked. Show reference ${unreservedResult.reference} at the counter.`);
    } catch (err) {
      notify("error", messageFor(err, "Could not book."));
    }
  }
</script>

<div class="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[1fr_360px]">
  <!-- Left: journey + seat map -->
  <div class="space-y-5">
    {#if loading}
      <div class="card preset-tonal-surface p-10 text-center opacity-70">
        Loading the journey.
      </div>
    {:else if !trip}
      <div class="card preset-tonal-error p-10 text-center">
        No trip is available right now. Please try again shortly.
      </div>
    {:else}
      <section class="card preset-tonal-surface p-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="badge-icon preset-filled-primary-500">
              <Icon name="train" class="h-5 w-5" />
            </span>
            <div>
              <p class="font-semibold">{legLabel(trip.stations, leg)}</p>
              <p class="text-sm opacity-70">{trip.service_date}</p>
            </div>
          </div>
          <div class="btn-group preset-outlined-surface-200-800 p-1 text-sm">
            <button
              type="button"
              class={`btn btn-sm ${mode === "reserved" ? "preset-filled-primary-500" : ""}`}
              onclick={() => (mode = "reserved")}
            >
              Reserved seat
            </button>
            <button
              type="button"
              class={`btn btn-sm ${mode === "unreserved" ? "preset-filled-primary-500" : ""}`}
              onclick={() => (mode = "unreserved")}
            >
              Unreserved
            </button>
          </div>
        </div>
        <JourneyPicker
          stations={trip.stations}
          bind:originSeq
          bind:destSeq
          bind:travelClass
          onchange={onLegChange}
        />
      </section>

      {#if mode === "reserved"}
        <div>
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-lg font-semibold">Choose your seat</h2>
            <span class="text-sm opacity-70">{seatMap.reservedFreeCount} of {seatMap.reservedTotal} free</span>
          </div>
          <SeatMap map={seatMap} onselect={selectSeat} />
        </div>
      {:else}
        <section class="card preset-tonal-surface p-6">
          <h2 class="text-lg font-semibold">Unreserved travel</h2>
          <p class="mt-1 text-sm opacity-70">
            Book with your NIC and get a reference. Your seat is assigned when you pay at the counter.
          </p>
          {#if unreservedResult}
            <div class="mt-4 card preset-tonal-success p-4">
              <p class="text-sm">Reference</p>
              <p class="font-mono text-xl font-bold tracking-wide">{unreservedResult.reference}</p>
              <p class="mt-1 text-sm opacity-80">Show this at the counter to pay and board.</p>
            </div>
          {/if}
        </section>
      {/if}
    {/if}
  </div>

  <!-- Right: summary + action -->
  <aside class="lg:sticky lg:top-6 lg:h-fit">
    <div class="card preset-tonal-surface space-y-4 p-5">
      <h2 class="text-base font-semibold">Your ticket</h2>

      {#if toast}
        <Toast kind={toast.kind} message={toast.message} onclose={() => (toast = null)} />
      {/if}

      <dl class="space-y-2 text-sm">
        <div class="flex justify-between"><dt class="opacity-70">Journey</dt><dd class="font-medium">{trip ? legLabel(trip.stations, leg) : "-"}</dd></div>
        <div class="flex justify-between"><dt class="opacity-70">Distance</dt><dd class="font-medium">{formatKm(distanceKm)}</dd></div>
        <div class="flex justify-between"><dt class="opacity-70">Class</dt><dd class="font-medium">{classLabel}</dd></div>
        {#if mode === "reserved"}
          <div class="flex justify-between"><dt class="opacity-70">Seat</dt><dd class="font-medium">{selectedSeatId || "-"}</dd></div>
        {/if}
      </dl>

      <div class="flex items-baseline justify-between border-t border-surface-200-800 pt-3">
        <span class="text-sm opacity-70">Fare</span>
        <span class="text-2xl font-bold">{quote ? formatMoney(quote.fare) : "-"}</span>
      </div>

      {#if mode === "reserved"}
        {#if bookState.status === "confirmed"}
          <div class="card preset-tonal-success p-4 text-center">
            <div class="badge-icon preset-filled-success-500 mx-auto mb-2">
              <Icon name="check" class="h-5 w-5" />
            </div>
            <p class="font-semibold">Ticket booked</p>
            <p class="mt-1 font-mono text-lg font-bold">{bookState.booking.reference}</p>
            <p class="text-sm opacity-80">Seat {bookState.booking.seat_id}</p>
            <button type="button" class="mt-3 text-sm font-medium underline-offset-2 hover:underline" onclick={bookAnother}>
              Book another seat
            </button>
          </div>
        {:else if soldOut}
          <div class="space-y-3">
            <p class="card preset-tonal-surface p-3 text-sm">
              No reserved seats free for this journey.
            </p>
            <PassengerForm bind:passenger />
            <button type="button" class="btn preset-outlined-primary-500 w-full" onclick={joinWaitlist}>
              Join the waitlist
            </button>
          </div>
        {:else}
          <div class="space-y-3">
            <PassengerForm bind:passenger disabled={busy} />
            <button
              type="button"
              class="btn preset-filled-primary-500 w-full"
              disabled={!selectedSeatId || !passengerReady || busy}
              onclick={reserveAndPay}
            >
              {#if busy}Reserving...{:else if !selectedSeatId}Select a seat{:else}Reserve & pay{/if}
            </button>
          </div>
        {/if}
      {:else}
        <div class="space-y-3">
          <PassengerForm bind:passenger />
          <button type="button" class="btn preset-filled-primary-500 w-full" onclick={bookUnreserved}>
            Book unreserved
          </button>
        </div>
      {/if}
    </div>
  </aside>
</div>
