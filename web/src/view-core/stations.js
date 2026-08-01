// L0 view-core: station + leg helpers over a trip's station list. Pure.
// A leg is the half-open station-sequence interval [originSeq, destSeq) (D2), so
// origin must sit strictly before destination and both must be real stations.

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** @param {Array<{seq:number}>} stations */
export function orderedStations(stations) {
  return [...(stations || [])].sort((a, b) => a.seq - b.seq);
}

export function stationBySeq(stations, seq) {
  return (stations || []).find((s) => s.seq === seq) || null;
}

/**
 * @param {{originSeq:number, destSeq:number}} leg
 * @param {Array<{seq:number}>} stations
 */
export function isValidLeg(leg, stations) {
  if (!leg) return false;
  const { originSeq, destSeq } = leg;
  if (!Number.isInteger(originSeq) || !Number.isInteger(destSeq)) return false;
  if (originSeq >= destSeq) return false;
  return stationBySeq(stations, originSeq) !== null && stationBySeq(stations, destSeq) !== null;
}

export function legLabel(stations, leg) {
  const from = stationBySeq(stations, leg?.originSeq);
  const to = stationBySeq(stations, leg?.destSeq);
  if (!from || !to) return "-";
  return `${from.name} → ${to.name}`;
}

/** Distance in km spanned by the leg (drives fares). 0 when the leg is unresolved. */
export function legDistanceKm(stations, leg) {
  const from = stationBySeq(stations, leg?.originSeq);
  const to = stationBySeq(stations, leg?.destSeq);
  if (!from || !to) return 0;
  return Math.max(0, to.km - from.km);
}

/** Parse an ISO "YYYY-MM-DD" into "Wed, 12 Aug 2026" without touching the wall clock. */
export function formatServiceDate(iso) {
  if (typeof iso !== "string") return "-";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  const [, y, mo, d] = m;
  const month = MONTHS[Number(mo) - 1];
  if (!month) return iso;
  return `${Number(d)} ${month} ${y}`;
}
