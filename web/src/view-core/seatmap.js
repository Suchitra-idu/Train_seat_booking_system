// L0 view-core: the seat-map grid model (D25). Pure - turns a trip's coach geometry
// (rows, "3-3" column pattern, exit rows) + per-leg availability + the current selection
// into rows of { left block, row number, right block } the UI just renders.
//
// Reserved seats are individually bookable; their status comes from the availability
// overlay. Unreserved coaches auto-assign a hidden seat at the counter (D3/D23), so their
// seats are shown for context but never selectable.

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

export function statusLabel(status) {
  return STATUS_LABEL[status] || status;
}

/** "3-3" -> [3, 3]; "2-2" -> [2, 2]; "1-0" -> [1, 0]. */
function blockSizes(columns) {
  return String(columns || "1-0")
    .split("-")
    .map((n) => Math.max(0, parseInt(n, 10) || 0));
}

function seatStatus(seat, { free, selectedSeatIds, hasAvailability }) {
  if (seat.coach_type === "UNRESERVED") return SEAT_STATUS.UNRESERVED;
  if (selectedSeatIds.has(seat.seat_id)) return SEAT_STATUS.SELECTED;
  if (!hasAvailability) return SEAT_STATUS.UNKNOWN;
  return free.has(seat.seat_id) ? SEAT_STATUS.FREE : SEAT_STATUS.TAKEN;
}

function toCell(seat, ctx) {
  const status = seatStatus(seat, ctx);
  const selectable = status === SEAT_STATUS.FREE || status === SEAT_STATUS.SELECTED;
  return {
    id: seat.seat_id,
    number: seat.number,
    row: seat.row,
    column: seat.column,
    status,
    selectable,
    label: `Seat ${seat.row}${seat.column}, ${classLabel(seat.travel_class)}, ${STATUS_LABEL[status]}`,
  };
}

function buildCoachGrid(coach, seats, ctx) {
  const [leftCount, rightCount] = blockSizes(coach.columns);
  const byRow = new Map();
  for (const seat of seats) {
    if (!byRow.has(seat.row)) byRow.set(seat.row, []);
    byRow.get(seat.row).push(seat);
  }
  const exitAfter = new Set(coach.exit_rows || []);

  const rows = [];
  for (let row = 1; row <= coach.rows; row++) {
    const rowSeats = (byRow.get(row) || []).sort((a, b) => a.column.localeCompare(b.column));
    rows.push({
      row,
      left: rowSeats.slice(0, leftCount).map((s) => toCell(s, ctx)),
      right: rowSeats.slice(leftCount, leftCount + rightCount).map((s) => toCell(s, ctx)),
      exitAfter: exitAfter.has(row),
    });
  }

  const reservedSeats = seats.filter((s) => s.coach_type === "RESERVED");
  return {
    code: coach.code,
    coachType: coach.coach_type,
    travelClass: coach.travel_class,
    rows,
    reservedTotal: reservedSeats.length,
    reservedFreeCount: ctx.hasAvailability
      ? reservedSeats.filter((s) => ctx.free.has(s.seat_id)).length
      : 0,
  };
}

/**
 * @param {object} args
 * @param {{coaches:Array, seats:Array}} args.trip
 * @param {object|null} args.availability  LegAvailabilityOut, or null before a leg is chosen
 * @param {Set<string>|string[]} [args.selectedSeatIds] a group booking may hold several seats at once
 */
export function buildSeatMap({ trip, availability, selectedSeatIds = [] }) {
  const coaches = trip?.coaches || [];
  const allSeats = trip?.seats || [];
  const ctx = {
    free: freeSeatIds(availability),
    selectedSeatIds: selectedSeatIds instanceof Set ? selectedSeatIds : new Set(selectedSeatIds),
    hasAvailability: !!availability,
  };

  const grids = coaches.map((coach) =>
    buildCoachGrid(
      coach,
      allSeats.filter((s) => s.coach === coach.code),
      ctx,
    ),
  );

  const reservedTotal = grids.reduce((sum, c) => sum + c.reservedTotal, 0);
  const reservedFreeCount = grids.reduce((sum, c) => sum + c.reservedFreeCount, 0);

  return {
    coaches: grids,
    reservedTotal,
    reservedFreeCount,
    hasUnreserved: coaches.some((c) => c.coach_type === "UNRESERVED"),
  };
}
