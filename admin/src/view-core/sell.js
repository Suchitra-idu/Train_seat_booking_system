// L0 view-core: the counter sell form as pure functions (D21, D23). No step machine is
// needed here, unlike the traveller wizard, a sale is one screen: search a journey, pick a
// train, pick a class, take cash. `sellReady` and `sellRequest` are the only two things
// worth pulling out of the component, whether the form can submit, and the exact shape the
// admin API expects.

export const TRAVEL_CLASSES = Object.freeze(["FIRST", "SECOND", "THIRD"]);

/** @param {{train: object|null, travelClass: string, passengerId: string, passengerName: string}} state */
export function sellReady(state) {
  return Boolean(
    state.train &&
      state.travelClass &&
      state.passengerId?.trim() &&
      state.passengerName?.trim(),
  );
}

/** Shapes the request body the admin API's `sell` method expects. */
export function sellRequest(state) {
  return {
    tripId: state.train.trip_id,
    originSeq: state.train.origin_seq,
    destSeq: state.train.dest_seq,
    travelClass: state.travelClass,
    passengerId: state.passengerId.trim(),
    passengerName: state.passengerName.trim(),
  };
}
