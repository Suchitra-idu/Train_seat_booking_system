// A demo trip shaped exactly like the API's TripOut, mirroring the backend demo seed
// (slr/app/demo_data.py). The fake client books against it in tests. Half-open legs run
// over station sequence 0..5 (D2).

export const DEMO_TRIP = Object.freeze({
  trip_id: "trip-1",
  route_code: "CMB-BAD",
  service_date: "2026-08-12",
  stations: [
    { code: "FORT", name: "Colombo Fort", seq: 0, km: 0 },
    { code: "RGM", name: "Ragama", seq: 1, km: 14 },
    { code: "GPH", name: "Gampaha", seq: 2, km: 28 },
    { code: "PDN", name: "Peradeniya", seq: 3, km: 116 },
    { code: "NNO", name: "Nanu Oya", seq: 4, km: 224 },
    { code: "BAD", name: "Badulla", seq: 5, km: 292 },
  ],
  seats: [
    { seat_id: "F1", coach: "A", coach_type: "RESERVED", travel_class: "FIRST", number: 1 },
    { seat_id: "F2", coach: "A", coach_type: "RESERVED", travel_class: "FIRST", number: 2 },
    { seat_id: "R1", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 1 },
    { seat_id: "R2", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 2 },
    { seat_id: "R3", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 3 },
    { seat_id: "R4", coach: "B", coach_type: "RESERVED", travel_class: "SECOND", number: 4 },
    { seat_id: "U1", coach: "C", coach_type: "UNRESERVED", travel_class: "SECOND", number: 1 },
    { seat_id: "U2", coach: "C", coach_type: "UNRESERVED", travel_class: "SECOND", number: 2 },
    { seat_id: "U3", coach: "C", coach_type: "UNRESERVED", travel_class: "SECOND", number: 3 },
  ],
});
