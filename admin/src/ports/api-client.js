// L1 port: the counter app's slice of the backend contract (D21). Two adapters implement
// it, the in-memory fake (drives component tests) and the real fetch client (validates
// every response against the OpenAPI schema, D13). The UI imports this interface only.

export * from "./errors.js";

/** method name → { schema: OpenAPI component, array?: boolean } */
export const RESPONSE_SCHEMA = Object.freeze({
  searchTrains: { schema: "TrainOptionOut", array: true },
  sell: { schema: "ReceiptOut" },
  verify: { schema: "VerifyOut" },
});

/**
 * @typedef {object} ApiClient
 * @property {(q: {originCode: string, destCode: string, serviceDate: string}) => Promise<object[]>} searchTrains
 * @property {(req: {tripId: string, originSeq: number, destSeq: number, travelClass: string, passengerId: string, passengerName: string}) => Promise<object>} sell
 * @property {(reference: string) => Promise<object>} verify
 */
export const ApiClient = {};
