// L1 port: the live availability feed (D7). The real adapter is an EventSource over the
// backend SSE stream; the fake is a controllable emitter for component tests. Both deliver
// deltas of the shape below and return an unsubscribe function.
//
// @typedef {object} AvailabilityDelta
// @property {string} trip_id
// @property {string} seat_id
// @property {number} origin_seq
// @property {number} dest_seq
// @property {string} status
//
// @typedef {object} AvailabilityStream
// @property {(tripId: string, handlers: {onDelta: (d: AvailabilityDelta) => void, onError?: (e: Error) => void}) => (() => void)} subscribe

/** The SSE event name the backend labels availability frames with (routes/stream.py). */
export const STREAM_EVENT = "availability";
