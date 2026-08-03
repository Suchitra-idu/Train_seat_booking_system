// L0 view-core: time/duration formatting. Pure. Times already arrive as "HH:MM" strings
// from the API (D22); this only formats duration and today's date for the search form.

export function formatDuration(minutes) {
  if (typeof minutes !== "number" || Number.isNaN(minutes) || minutes < 0) return "-";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Today as "YYYY-MM-DD" from a Date, for the search form's min/default date. */
export function isoDate(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
