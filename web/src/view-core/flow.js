// L0 view-core: the booking wizard as a pure step reducer (D26). One funnel -
// landing -> search -> trains -> seats -> passenger -> receipt - with back legal from
// every step. Keeping this pure means every transition (including "seat taken -> back to
// seats" and "a removed seat un-links anyone marked as its child") is a unit-tested
// assertion, not a click-through.
//
// Seats are a group cart, not a single pick: a booking session can carry several seats,
// each with its own named passenger, so a group of friends can book together in one pass.
// A passenger may be flagged as travelling with ("child of") the entry directly above it
// in pick order - a display link only, not a fare rule.

export const STEPS = Object.freeze([
  "landing",
  "search",
  "trains",
  "seats",
  "passenger",
  "receipt",
]);

export const initialFlowState = Object.freeze({
  step: "landing",
  journey: null, // { originCode, destCode, serviceDate }
  train: null, // TrainOptionOut
  seatIds: [], // selection order
  passengers: {}, // seatId -> { name, nic, childOfSeatId }
  tickets: [], // [{ seatId, childOfSeatId, receipt }] after BOOKED
  error: null,
});

function stepIndex(step) {
  return STEPS.indexOf(step);
}

export function canGoBack(state) {
  return stepIndex(state.step) > 0 && state.step !== "receipt";
}

function blankPassenger() {
  return { name: "", nic: "", childOfSeatId: null };
}

/** Drop a seat and unlink anyone who named it as the passenger they're travelling with -
 * a stale link would otherwise point at a seat that no longer exists in the cart. */
function withoutSeat(state, seatId) {
  const seatIds = state.seatIds.filter((id) => id !== seatId);
  const passengers = {};
  for (const id of seatIds) {
    const p = state.passengers[id] || blankPassenger();
    passengers[id] = p.childOfSeatId === seatId ? { ...p, childOfSeatId: null } : p;
  }
  return { seatIds, passengers };
}

export function flowReducer(state, action) {
  switch (action.type) {
    case "START":
      return { ...initialFlowState, step: "search" };

    case "SEARCHED":
      return { ...state, step: "trains", journey: action.journey, error: null };

    case "TRAIN_SELECTED":
      return { ...state, step: "seats", train: action.train, seatIds: [], passengers: {}, error: null };

    case "SEAT_TOGGLED": {
      const { seatId } = action;
      if (state.seatIds.includes(seatId)) {
        const { seatIds, passengers } = withoutSeat(state, seatId);
        return { ...state, seatIds, passengers, error: null };
      }
      return { ...state, seatIds: [...state.seatIds, seatId], error: null };
    }

    case "SEATS_CONFIRMED": {
      // Seed a blank passenger for any newly-picked seat; keep entries already typed for
      // seats still in the cart if the traveller went back and returned.
      const passengers = { ...state.passengers };
      for (const seatId of state.seatIds) {
        if (!passengers[seatId]) passengers[seatId] = blankPassenger();
      }
      return { ...state, step: "passenger", passengers, error: null };
    }

    case "PASSENGER_UPDATED":
      return {
        ...state,
        passengers: {
          ...state.passengers,
          [action.seatId]: { ...state.passengers[action.seatId], ...action.patch },
        },
      };

    case "BOOKED":
      return { ...state, step: "receipt", tickets: action.tickets, error: null };

    // A seat vanished between pick and hold (D2 race), mid-group-checkout: drop just that
    // seat and its passenger row, back to the seat map to pick a replacement.
    case "SEAT_REMOVED_CONFLICT": {
      const { seatIds, passengers } = withoutSeat(state, action.seatId);
      return { ...state, step: "seats", seatIds, passengers, error: action.message || "That seat was just taken." };
    }

    case "BACK": {
      const idx = stepIndex(state.step);
      if (idx <= 0 || state.step === "receipt") return state;
      return { ...state, step: STEPS[idx - 1], error: null };
    }

    case "ERROR_CLEARED":
      return { ...state, error: null };

    case "RESTART":
      return { ...initialFlowState };

    default:
      return state;
  }
}
