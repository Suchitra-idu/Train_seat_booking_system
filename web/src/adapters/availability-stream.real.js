// L2: the real availability feed over Server-Sent Events (D7). Wraps EventSource; the
// backend labels frames with the "availability" event. `EventSourceImpl` is injectable for
// tests. subscribe() returns an unsubscribe that closes the connection.

import { STREAM_EVENT } from "../ports/availability-stream.js";

export class RealAvailabilityStream {
  constructor({ baseUrl = "", EventSourceImpl } = {}) {
    this._base = baseUrl.replace(/\/$/, "");
    this._ES = EventSourceImpl || (typeof EventSource !== "undefined" ? EventSource : null);
  }

  subscribe(tripId, { onDelta, onError } = {}) {
    if (!this._ES) return () => {};
    const source = new this._ES(`${this._base}/trips/${encodeURIComponent(tripId)}/stream`);
    source.addEventListener(STREAM_EVENT, (e) => {
      try {
        onDelta?.(JSON.parse(e.data));
      } catch (err) {
        onError?.(err);
      }
    });
    source.addEventListener("error", (e) => onError?.(e));
    return () => source.close();
  }
}
