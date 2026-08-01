// L1 port: the ApiClient contract the UI depends on. Two adapters implement it - the
// in-memory fake (drives component tests) and the real fetch client (validates every
// response against the OpenAPI schema, D13). The UI imports this interface only, never an
// adapter (dependency-cruiser enforces it).
//
// RESPONSE_SCHEMA binds each method to the OpenAPI component it must return, so the real
// client and the fake-conformance test validate against one shared source of truth.

export * from "./errors.js";

/** method name → { schema: OpenAPI component, array?: boolean } */
export const RESPONSE_SCHEMA = Object.freeze({
  searchTrains: { schema: "TrainOptionOut", array: true },
  getTrip: { schema: "TripOut" },
  availability: { schema: "LegAvailabilityOut" },
  quote: { schema: "QuoteOut" },
  hold: { schema: "BookingOut" },
  confirm: { schema: "ReceiptOut" },
  cancel: { schema: "BookingOut" },
});

/**
 * @typedef {object} ApiClient
 * @property {(q: {originCode: string, destCode: string, serviceDate: string}) => Promise<object[]>} searchTrains
 * @property {(tripId: string) => Promise<object>} getTrip
 * @property {(tripId: string, leg: {originSeq: number, destSeq: number}) => Promise<object>} availability
 * @property {(req: object) => Promise<object>} quote
 * @property {(req: object, opts?: {idempotencyKey?: string}) => Promise<object>} hold
 * @property {(bookingId: string) => Promise<object>} confirm
 * @property {(bookingId: string) => Promise<object>} cancel
 */
export const ApiClient = {};
