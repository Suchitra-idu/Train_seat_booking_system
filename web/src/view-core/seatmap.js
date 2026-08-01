// L0 view-core: the seat-map layout model. Pure - turns a trip + per-leg availability
// (+ the current selection) into coaches of status-tagged seats the UI just renders.
//
// Reserved seats are individually bookable; their status comes from the availability
// overlay. Unreserved coaches auto-assign a hidden seat at the counter (D3/D21), so their
// seats are shown for context but never selectable. free_count from the API spans every
// seat including unreserved virtuals, so "sold out" for the reservable map is recomputed
// here over reserved seats only.

import { freeSeatIds } from "./availability.js";

export const SEAT_STATUS = {
  FREE: "free",
  TAKEN: "taken",
  SELECTED: "selected",
  UNRESERVED: "unreserved",
  UNKNOWN: "unknown",
};

const STATUS_LABEL = {
  free: "available",
  taken: "booked",
  selected: "selected",
  unreserved: "unreserved (assigned at counter)",
  unknown: "availability not loaded",
};

const CLASS_LABEL = { FIRST: "1st class", SECOND: "2nd class", THIRD: "3rd class" };

export function classLabel(travelClass) {
  return CLASS_LABEL[travelClass] || travelClass || "";
}

function seatStatus(seat, { free, selectedSeatId, hasAvailability }) {
  if (seat.coach_type === "UNRESERVED") return SEAT_STATUS.UNRESERVED;
  if (seat.seat_id === selectedSeatId) return SEAT_STATUS.SELECTED;
  if (!hasAvailability) return SEAT_STATUS.UNKNOWN;
  return free.has(seat.seat_id) ? SEAT_STATUS.FREE : SEAT_STATUS.TAKEN;
}

/**
 * @param {object} args
 * @param {{seats:Array}} args.trip
 * @param {object|null} args.availability  LegAvailabilityOut, or null before a leg is chosen
 * @param {string|null} [args.selectedSeatId]
 */
export function buildSeatMap({ trip, availability, selectedSeatId = null }) {
  const seats = trip?.seats || [];
  const hasAvailability = !!availability;
  const free = freeSeatIds(availability);

  const byCoach = new Map();
  for (const s of seats) {
    if (!byCoach.has(s.coach)) {
      byCoach.set(s.coach, {
        code: s.coach,
        coachType: s.coach_type,
        travelClass: s.travel_class,
        seats: [],
      });
    }
    const status = seatStatus(s, { free, selectedSeatId, hasAvailability });
    const selectable = status === SEAT_STATUS.FREE || status === SEAT_STATUS.SELECTED;
    byCoach.get(s.coach).seats.push({
      id: s.seat_id,
      number: s.number,
      coachType: s.coach_type,
      travelClass: s.travel_class,
      status,
      selectable,
      label: `Seat ${s.seat_id}, ${classLabel(s.travel_class)}, ${STATUS_LABEL[status]}`,
    });
  }

  const coaches = [...byCoach.values()]
    .sort((a, b) => a.code.localeCompare(b.code))
    .map((c) => ({ ...c, seats: c.seats.sort((a, b) => a.number - b.number) }));

  const reservedSeats = seats.filter((s) => s.coach_type === "RESERVED");
  const reservedFreeCount = hasAvailability
    ? reservedSeats.filter((s) => free.has(s.seat_id)).length
    : 0;

  return {
    coaches,
    reservedTotal: reservedSeats.length,
    reservedFreeCount,
    hasUnreserved: seats.some((s) => s.coach_type === "UNRESERVED"),
  };
}

export function statusLabel(status) {
  return STATUS_LABEL[status] || status;
}
