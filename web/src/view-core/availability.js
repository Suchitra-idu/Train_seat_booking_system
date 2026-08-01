// L0 view-core: read a LegAvailabilityOut into quick lookups. Pure.

/** @param {{seats?: Array<{seat_id:string, available:boolean}>}} availability */
export function freeSeatIds(availability) {
  const set = new Set();
  for (const s of availability?.seats || []) {
    if (s.available) set.add(s.seat_id);
  }
  return set;
}

export function isSeatAvailable(availability, seatId) {
  return freeSeatIds(availability).has(seatId);
}

export function freeCount(availability) {
  if (typeof availability?.free_count === "number") return availability.free_count;
  return freeSeatIds(availability).size;
}

/** True when the leg is sold out for reservable seats - the cue to offer the waitlist. */
export function isSoldOut(availability) {
  return !!availability && freeCount(availability) === 0;
}
