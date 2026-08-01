// L2: a controllable availability feed for component tests. `emit(delta)` pushes a frame
// to every live subscriber of that trip, so a test can simulate another user booking a seat
// and assert the map greys out live.

export class FakeAvailabilityStream {
  constructor() {
    this._subs = new Map(); // tripId -> Set<onDelta>
  }

  subscribe(tripId, { onDelta } = {}) {
    if (!this._subs.has(tripId)) this._subs.set(tripId, new Set());
    const set = this._subs.get(tripId);
    set.add(onDelta);
    return () => set.delete(onDelta);
  }

  emit(delta) {
    for (const onDelta of this._subs.get(delta.trip_id) || []) onDelta(delta);
  }
}
