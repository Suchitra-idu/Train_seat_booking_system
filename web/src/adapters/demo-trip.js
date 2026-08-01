// A demo trip shaped exactly like the API's TripOut (D22, D25), mirroring the backend's
// seeded timetable (config/timetable.json, pattern "1005"). The fake client books against
// it in tests. Half-open legs run over station sequence 0..5 (D2).

const COLUMN_LETTERS = "ABCDEFGH";

/** Mirrors the backend's column_labels()+build_coach() (timetable_config.py): letters run
 * left-to-right across the whole row, seat id is `{coach}{row}{column}`. */
function buildCoach(code, { coachType, travelClass, rows, columns, exitRows = [] }) {
  const perBlock = columns.split("-").map(Number);
  const letters = COLUMN_LETTERS.slice(0, perBlock.reduce((a, b) => a + b, 0)).split("");
  const seats = [];
  for (let row = 1; row <= rows; row++) {
    letters.forEach((column, index) => {
      seats.push({
        seat_id: `${code}${row}${column}`,
        coach: code,
        coach_type: coachType,
        travel_class: travelClass,
        number: (row - 1) * letters.length + index + 1,
        row,
        column,
      });
    });
  }
  const coach = {
    code,
    coach_type: coachType,
    travel_class: travelClass,
    rows,
    columns,
    exit_rows: exitRows,
  };
  return { coach, seats };
}

const { coach: coachA, seats: seatsA } = buildCoach("A", {
  coachType: "RESERVED",
  travelClass: "SECOND",
  rows: 3,
  columns: "2-2",
  exitRows: [2],
});
const { coach: coachB, seats: seatsB } = buildCoach("B", {
  coachType: "UNRESERVED",
  travelClass: "SECOND",
  rows: 2,
  columns: "2-2",
});

export const DEMO_TRIP = Object.freeze({
  trip_id: "1005:2026-08-12",
  route_code: "CMB-BAD",
  service_date: "2026-08-12",
  train_no: "1005",
  train_name: "Podi Menike",
  stations: [
    { code: "FORT", name: "Colombo Fort", seq: 0, km: 0 },
    { code: "RGM", name: "Ragama", seq: 1, km: 14 },
    { code: "GPH", name: "Gampaha", seq: 2, km: 28 },
    { code: "KDY", name: "Kandy", seq: 3, km: 121 },
    { code: "NNO", name: "Nanu Oya", seq: 4, km: 224 },
    { code: "BAD", name: "Badulla", seq: 5, km: 292 },
  ],
  stops: [
    { station_seq: 0, arrive: null, depart: "05:55" },
    { station_seq: 1, arrive: "06:18", depart: "06:20" },
    { station_seq: 2, arrive: "06:38", depart: "06:40" },
    { station_seq: 3, arrive: "08:47", depart: "08:55" },
    { station_seq: 4, arrive: "12:25", depart: "12:35" },
    { station_seq: 5, arrive: "15:55", depart: null },
  ],
  coaches: [coachA, coachB],
  seats: [...seatsA, ...seatsB],
});

/** A second train on the same date, so search results show more than one row. */
export const DEMO_TRIP_2 = Object.freeze({
  ...DEMO_TRIP,
  trip_id: "1015:2026-08-12",
  train_no: "1015",
  train_name: "Udarata Menike",
  stops: [
    { station_seq: 0, arrive: null, depart: "09:45" },
    { station_seq: 1, arrive: "10:08", depart: "10:10" },
    { station_seq: 2, arrive: "10:28", depart: "10:30" },
    { station_seq: 3, arrive: "12:47", depart: "12:55" },
    { station_seq: 4, arrive: "16:00", depart: "16:10" },
    { station_seq: 5, arrive: "19:20", depart: null },
  ],
});
