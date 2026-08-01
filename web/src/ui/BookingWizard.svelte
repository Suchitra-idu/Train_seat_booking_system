<script>
  // L3: the booking wizard (D26) - landing -> search -> trains -> seats -> passenger ->
  // receipt, driven by the pure flow reducer (view-core/flow.js). This component owns the
  // async data each step needs (search results, the loaded trip, availability, per-seat
  // quotes); the reducer owns only the step and the choices made along the way.
  //
  // A booking is a group cart: several seats can be picked at once, each gets its own
  // named passenger, and one can be flagged as travelling with ("child of") the entry
  // above it. Paying is all-or-nothing for the group - if any seat in the cart is lost to
  // a race or the charge fails partway, every hold made so far in this batch is released
  // rather than leaving some of the group booked and others stuck.
  import Landing from "./Landing.svelte";
  import JourneySearch from "./JourneySearch.svelte";
  import TrainList from "./TrainList.svelte";
  import SeatMap from "./SeatMap.svelte";
  import PassengerRow from "./PassengerRow.svelte";
  import Receipt from "./Receipt.svelte";
  import Toast from "./Toast.svelte";
  import Icon from "./Icon.svelte";

  import { flowReducer, initialFlowState } from "../view-core/flow.js";
  import { buildSeatMap } from "../view-core/seatmap.js";
  import { legLabel, legDistanceKm } from "../view-core/stations.js";
  import { formatMoney, formatKm } from "../view-core/money.js";
  import { STORAGE_KEYS } from "../ports/storage.js";
  import { ConflictError, RateLimitError, PaymentError, ValidationError } from "../ports/errors.js";

  let { api, stream = null, storage = null, exporter = null } = $props();

  let flow = $state(initialFlowState);
  let trainOptions = $state([]);
  let trip = $state(null);
  let availability = $state(null);
  let seatQuotes = $state({}); // seatId -> QuoteOut
  let toast = $state(null);
  let busy = $state(false);
  let unsubscribe = null;

  const leg = $derived(flow.train ? { originSeq: flow.train.origin_seq, destSeq: flow.train.dest_seq } : null);
  const seatMap = $derived(
    trip ? buildSeatMap({ trip, availability, selectedSeatIds: flow.seatIds }) : null,
  );
  const totalFareCents = $derived(
    Object.values(seatQuotes).reduce((sum, q) => sum + (q?.fare?.cents ?? 0), 0),
  );
  // A linked ("travelling with") passenger has no NIC field of their own - it's locked
  // and resolved from the nearest independent passenger up the chain, so readiness and
  // the actual hold both walk that chain rather than reading passenger.nic directly.
  function resolveNic(seatId) {
    let current = flow.passengers[seatId];
    let guard = flow.seatIds.length + 1; // structurally acyclic, but never spin forever
    while (current?.childOfSeatId && guard-- > 0) {
      current = flow.passengers[current.childOfSeatId];
    }
    return current?.nic?.trim() ?? "";
  }

  const passengerReady = $derived(
    flow.seatIds.length > 0 &&
      flow.seatIds.every((id) => {
        const p = flow.passengers[id];
        return p && p.name.trim().length > 0 && resolveNic(id).length > 0;
      }),
  );

  const dispatch = (action) => (flow = flowReducer(flow, action));
  const notify = (kind, message) => (toast = { kind, message });
  const messageFor = (err, fallback) => err?.detail || err?.message || fallback;

  // Exported so the app shell's header "home" button can reach across from a sibling
  // component (bind:this in App.svelte).
  export function goHome() {
    unsubscribe?.();
    unsubscribe = null;
    trip = null;
    availability = null;
    seatQuotes = {};
    toast = null;
    dispatch({ type: "RESTART" });
  }

  function goBack() {
    if (flow.step === "seats") {
      unsubscribe?.();
      unsubscribe = null;
    }
    dispatch({ type: "BACK" });
  }

  async function handleSearch(journey) {
    busy = true;
    try {
      trainOptions = await api.searchTrains(journey);
      dispatch({ type: "SEARCHED", journey });
    } catch (err) {
      notify("error", messageFor(err, "Could not search trains."));
    } finally {
      busy = false;
    }
  }

  async function handleSelectTrain(train) {
    busy = true;
    seatQuotes = {};
    try {
      trip = await api.getTrip(train.trip_id);
      dispatch({ type: "TRAIN_SELECTED", train });
      await refreshAvailability(train);
      unsubscribe = stream?.subscribe(train.trip_id, { onDelta: () => refreshAvailability(train) });
    } catch (err) {
      notify("error", messageFor(err, "Could not load that train."));
    } finally {
      busy = false;
    }
  }

  async function refreshAvailability(train) {
    try {
      availability = await api.availability(train.trip_id, {
        originSeq: train.origin_seq,
        destSeq: train.dest_seq,
      });
    } catch (err) {
      notify("error", messageFor(err, "Could not load availability."));
    }
  }

  function coachOfSeat(seatId) {
    return seatMap.coaches.find((c) =>
      c.rows.some((r) => r.left.some((s) => s.id === seatId) || r.right.some((s) => s.id === seatId)),
    );
  }

  async function handleToggleSeat(seatId) {
    const adding = !flow.seatIds.includes(seatId);
    dispatch({ type: "SEAT_TOGGLED", seatId });
    if (!adding) {
      const { [seatId]: _dropped, ...rest } = seatQuotes;
      seatQuotes = rest;
      return;
    }
    try {
      const quote = await api.quote({
        tripId: flow.train.trip_id,
        originSeq: flow.train.origin_seq,
        destSeq: flow.train.dest_seq,
        travelClass: coachOfSeat(seatId)?.travelClass,
      });
      seatQuotes = { ...seatQuotes, [seatId]: quote };
    } catch {
      /* the fare summary just skips this seat; it is still pickable */
    }
  }

  function handleSeatsConfirmed() {
    dispatch({ type: "SEATS_CONFIRMED" });
    // Autofill the first seat from a remembered passenger (a returning solo traveller);
    // a group booking always types names for everyone else.
    const saved = storage?.get(STORAGE_KEYS.PASSENGER);
    const firstSeatId = flow.seatIds[0];
    if (saved?.nic && firstSeatId) {
      dispatch({ type: "PASSENGER_UPDATED", seatId: firstSeatId, patch: saved });
    }
  }

  function removeSeat(seatId) {
    dispatch({ type: "SEAT_TOGGLED", seatId });
    const { [seatId]: _dropped, ...rest } = seatQuotes;
    seatQuotes = rest;
    if (flow.seatIds.length === 0) dispatch({ type: "BACK" });
  }

  function persistPrimaryPassenger() {
    const first = flow.passengers[flow.seatIds[0]];
    if (first?.nic) storage?.set(STORAGE_KEYS.PASSENGER, { name: first.name, nic: first.nic });
  }

  // One user action for the whole group: reserve every seat and pay. The hold is an
  // internal step (D6), never surfaced as separate per-seat actions.
  async function reserveAndPayGroup() {
    if (!passengerReady || busy) return;
    persistPrimaryPassenger();
    busy = true;

    const seatIds = flow.seatIds;
    const held = [];
    let conflictSeatId = null;
    let holdErr = null;

    for (const seatId of seatIds) {
      const passenger = flow.passengers[seatId];
      const nic = resolveNic(seatId);
      try {
        const booking = await api.hold(
          {
            tripId: flow.train.trip_id,
            seatId,
            originSeq: flow.train.origin_seq,
            destSeq: flow.train.dest_seq,
            passengerId: nic,
            passengerName: passenger.name.trim(),
          },
          {
            idempotencyKey: `hold:${seatId}:${flow.train.origin_seq}-${flow.train.dest_seq}:${nic}`,
          },
        );
        held.push({ seatId, booking });
      } catch (err) {
        conflictSeatId = seatId;
        holdErr = err;
        break;
      }
    }

    if (holdErr) {
      await releaseAll(held);
      busy = false;
      handleGroupHoldError(holdErr, conflictSeatId);
      return;
    }

    try {
      const tickets = [];
      for (const { seatId, booking } of held) {
        const receipt = await api.confirm(booking.booking_id);
        tickets.push({ seatId, childOfSeatId: flow.passengers[seatId].childOfSeatId, receipt });
      }
      dispatch({ type: "BOOKED", tickets });
    } catch (err) {
      await releaseAll(held);
      notify(
        "error",
        err instanceof PaymentError
          ? "Payment could not be completed for the group. Please try again."
          : messageFor(err, "Could not complete the booking."),
      );
    } finally {
      busy = false;
    }
  }

  async function releaseAll(held) {
    await Promise.all(held.map((h) => api.cancel(h.booking.booking_id).catch(() => {})));
  }

  function handleGroupHoldError(err, conflictSeatId) {
    if (err instanceof ConflictError) {
      dispatch({
        type: "SEAT_REMOVED_CONFLICT",
        seatId: conflictSeatId,
        message: "That seat was just taken. Please pick another for the group.",
      });
      refreshAvailability(flow.train);
    } else if (err instanceof RateLimitError) {
      notify("error", messageFor(err, "Too many requests. Please slow down."));
    } else if (err instanceof ValidationError) {
      notify("error", messageFor(err, "That request is not valid."));
    } else {
      notify("error", messageFor(err, "Could not reserve the seats."));
    }
  }
</script>

<div class="mx-auto max-w-5xl px-4 py-6">
  {#if toast}
    <div class="mb-4">
      <Toast kind={toast.kind} message={toast.message} onclose={() => (toast = null)} />
    </div>
  {/if}
  {#if flow.error}
    <div class="mb-4">
      <Toast kind="error" message={flow.error} onclose={() => dispatch({ type: "ERROR_CLEARED" })} />
    </div>
  {/if}

  {#if flow.step === "landing"}
    <Landing onreserve={() => dispatch({ type: "START" })} />
  {:else if flow.step === "search"}
    <JourneySearch onsearch={handleSearch} />
  {:else if flow.step === "trains"}
    <TrainList options={trainOptions} journey={flow.journey} onback={goBack} onselect={handleSelectTrain} />
  {:else if flow.step === "seats" && seatMap}
    <div class="space-y-4 pb-24">
      <button type="button" class="flex items-center gap-1 text-sm font-medium opacity-70 hover:opacity-100" onclick={goBack}>
        <Icon name="chevron-left" class="size-4" />
        Change train
      </button>
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">
          {flow.train.train_no} &middot; {legLabel(trip.stations, { originSeq: leg.originSeq, destSeq: leg.destSeq })}
        </h2>
        <span class="text-sm opacity-70">{formatKm(legDistanceKm(trip.stations, leg))}</span>
      </div>
      <SeatMap map={seatMap} ontoggle={handleToggleSeat} />
    </div>

    {#if flow.seatIds.length > 0}
      <div class="fixed inset-x-0 bottom-0 z-10 border-t border-surface-200-800 preset-tonal-surface p-4">
        <div class="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div class="text-sm">
            <span class="font-semibold">{flow.seatIds.length} seat{flow.seatIds.length > 1 ? "s" : ""} selected</span>
            <span class="opacity-70"> &middot; {formatMoney({ cents: totalFareCents, currency: "LKR" })}</span>
          </div>
          <button type="button" class="btn preset-filled-primary-500" onclick={handleSeatsConfirmed}>
            Continue
          </button>
        </div>
      </div>
    {/if}
  {:else if flow.step === "passenger"}
    <div class="mx-auto max-w-md space-y-5">
      <button type="button" class="flex items-center gap-1 text-sm font-medium opacity-70 hover:opacity-100" onclick={goBack}>
        <Icon name="chevron-left" class="size-4" />
        Change seats
      </button>

      <h2 class="text-base font-semibold">Passenger details</h2>

      {#each flow.seatIds as seatId, i (seatId)}
        <PassengerRow
          seatLabel={seatId}
          passenger={flow.passengers[seatId]}
          parentSeatId={i > 0 ? flow.seatIds[i - 1] : null}
          parentName={i > 0 ? flow.passengers[flow.seatIds[i - 1]]?.name : ""}
          parentNic={i > 0 ? resolveNic(flow.seatIds[i - 1]) : ""}
          disabled={busy}
          oninput={(patch) => dispatch({ type: "PASSENGER_UPDATED", seatId, patch })}
          onremove={flow.seatIds.length > 1 ? () => removeSeat(seatId) : undefined}
        />
      {/each}

      <div class="card preset-tonal-surface space-y-3 p-5">
        <div class="flex items-baseline justify-between">
          <span class="opacity-70">Total for {flow.seatIds.length} seat{flow.seatIds.length > 1 ? "s" : ""}</span>
          <span class="text-xl font-bold">{formatMoney({ cents: totalFareCents, currency: "LKR" })}</span>
        </div>
        <button
          type="button"
          class="btn preset-filled-primary-500 w-full"
          disabled={!passengerReady || busy}
          onclick={reserveAndPayGroup}
        >
          {busy ? "Reserving..." : "Reserve & pay"}
        </button>
      </div>
    </div>
  {:else if flow.step === "receipt" && flow.tickets.length > 0}
    <Receipt tickets={flow.tickets} {exporter} onbookanother={goHome} />
  {/if}
</div>
