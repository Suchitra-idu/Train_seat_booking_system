// L0 view-core: the reserved hold→confirm flow as a pure reducer (D6 lifecycle at the UI
// edge). The UI dispatches events from its port calls; this decides the next state. Keeping
// it pure means the whole flow - including the nasty 409-on-hold race - is unit-tested with
// no network, no components, no clock.

export const initialBookingState = Object.freeze({
  status: "idle", // idle | quoting | quoted | holding | held | confirming | confirmed | cancelling | cancelled | error
  quote: null,
  booking: null,
  error: null, // { kind, message }
});

const BUSY = new Set(["quoting", "holding", "confirming", "cancelling"]);

export function isBusy(state) {
  return BUSY.has(state.status);
}

/** A conflict (409) leaves the flow re-pickable: the seat is gone, the quote stands. */
export function canRepick(state) {
  return state.status === "error" && state.error?.kind === "conflict";
}

export function bookingReducer(state, action) {
  switch (action.type) {
    case "QUOTE_REQUESTED":
      return { ...state, status: "quoting", error: null };
    case "QUOTE_SUCCEEDED":
      return { ...state, status: "quoted", quote: action.quote, error: null };

    case "HOLD_REQUESTED":
      return { ...state, status: "holding", error: null };
    case "HOLD_SUCCEEDED":
      return { ...state, status: "held", booking: action.booking, error: null };
    case "HOLD_CONFLICT":
      return {
        ...state,
        status: "error",
        booking: null,
        error: { kind: "conflict", message: action.message || "That seat was just taken." },
      };

    case "CONFIRM_REQUESTED":
      return { ...state, status: "confirming", error: null };
    case "CONFIRM_SUCCEEDED":
      return { ...state, status: "confirmed", booking: action.booking, error: null };

    case "CANCEL_REQUESTED":
      return { ...state, status: "cancelling", error: null };
    case "CANCEL_SUCCEEDED":
      return { ...state, status: "cancelled", booking: action.booking, error: null };

    case "FAILED":
      return {
        ...state,
        status: "error",
        error: { kind: action.kind || "error", message: action.message || "Something went wrong." },
      };

    case "RESET":
      return { ...initialBookingState };

    default:
      return state;
  }
}
