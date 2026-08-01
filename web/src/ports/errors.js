// L1 port contract: the typed failures every ApiClient (real or fake) raises, so the UI
// handles a lost-seat race the same way regardless of which adapter is wired. The real
// client maps HTTP status → these; the fake throws them directly; components catch them.

export class ApiError extends Error {
  constructor(message, { status = 0, detail = "" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** 409 - the seat/leg was taken between availability and hold (the D2 race). */
export class ConflictError extends ApiError {
  constructor(message = "That seat was just taken.", opts) {
    super(message, { status: 409, ...opts });
    this.name = "ConflictError";
  }
}

/** 429 - anti-tout velocity/abuse limit tripped (D9). */
export class RateLimitError extends ApiError {
  constructor(message = "Too many requests. Please slow down.", opts) {
    super(message, { status: 429, ...opts });
    this.name = "RateLimitError";
  }
}

/** 422 - the request was malformed (bad leg, off-route, non-reservable seat). */
export class ValidationError extends ApiError {
  constructor(message = "That request is not valid.", opts) {
    super(message, { status: 422, ...opts });
    this.name = "ValidationError";
  }
}

/** 402 - mock payment declined (D17). */
export class PaymentError extends ApiError {
  constructor(message = "Payment was declined.", opts) {
    super(message, { status: 402, ...opts });
    this.name = "PaymentError";
  }
}

/** 404 - no such trip/booking/reference. */
export class NotFoundError extends ApiError {
  constructor(message = "Not found.", opts) {
    super(message, { status: 404, ...opts });
    this.name = "NotFoundError";
  }
}

/** A response did not match the OpenAPI contract (D13). A red build, not a silent bug. */
export class SchemaError extends ApiError {
  constructor(message, { schema = "", issues = [] } = {}) {
    super(message, { status: 0 });
    this.name = "SchemaError";
    this.schema = schema;
    this.issues = issues;
  }
}

export function errorForStatus(status, message, detail) {
  const opts = { detail };
  switch (status) {
    case 409: return new ConflictError(message || undefined, opts);
    case 429: return new RateLimitError(message || undefined, opts);
    case 422: return new ValidationError(message || undefined, opts);
    case 402: return new PaymentError(message || undefined, opts);
    case 404: return new NotFoundError(message || undefined, opts);
    default: return new ApiError(message || `Request failed (${status})`, { status, detail });
  }
}
