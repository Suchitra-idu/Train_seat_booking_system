// L2: the in-memory ApiClient (D21, D23). Replicates just enough of the backend to drive
// component tests with zero infrastructure: search across a timetable, and one-transaction
// unreserved sale that packs a free seat or predicts a standing spot when none is free.
// Output shapes match the OpenAPI contract exactly (fake-conforms-to-contract proves it).

import { ConflictError, NotFoundError, ValidationError } from "../ports/errors.js";
import { DEMO_TRIP } from "./demo-trip.js";

const CLASS_MULT = { FIRST: 2.0, SECOND: 1.0, THIRD: 0.7 };
const CLASS_ORDER = ["FIRST", "SECOND", "THIRD"];
const RATE_PER_KM_CENTS = 685;
const STANDING_CAPACITY_PER_COACH = 2;

const overlaps = (a, b) => a.originSeq < b.destSeq && b.originSeq < a.destSeq;
const clone = (o) => JSON.parse(JSON.stringify(o));

function minutesOf(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export class FakeApiClient {
  constructor({ trips = [DEMO_TRIP], now = 1000 } = {}) {
    this._trips = new Map(clone(trips).map((t) => [t.trip_id, t]));
    this._sales = []; // seated: {seatId, leg}; standing: {seatId: null}
    this._now = now;
    this._seq = 0;
  }

  // ─── search (same shape as the traveller app's) ────────────────────────
  async searchTrains({ originCode, destCode, serviceDate }) {
    const options = [];
    for (const trip of this._trips.values()) {
      if (trip.service_date !== serviceDate) continue;
      const option = this._trainOption(trip, originCode, destCode);
      if (option) options.push(option);
    }
    return options;
  }

  // ─── the counter's two jobs ─────────────────────────────────────────────
  async sell({ tripId, originSeq, destSeq, travelClass, passengerId, passengerName }) {
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    const leg = { originSeq, destSeq };
    const coachSeats = trip.seats.filter(
      (s) => s.coach_type === "UNRESERVED" && s.travel_class === travelClass,
    );
    if (coachSeats.length === 0) {
      throw new ValidationError(`no unreserved ${travelClass} coach on this trip`);
    }

    const free = coachSeats.find((s) => !this._activeForSeat(tripId, s.seat_id).some((sale) => overlaps(sale.leg, leg)));
    const sale = {
      id: `s-${++this._seq}`,
      trip_id: tripId,
      seat_id: free?.seat_id ?? null,
      leg: free ? leg : null,
      passenger_id: passengerId,
      passenger_name: passengerName,
      travel_class: travelClass,
      status: free ? "CONFIRMED" : "STANDING",
      reference: `SLR-${String(this._seq).padStart(6, "0")}`,
    };

    if (!free) {
      const standingCount = this._sales.filter(
        (s) => s.trip_id === tripId && s.travel_class === travelClass && s.status === "STANDING",
      ).length;
      if (standingCount >= STANDING_CAPACITY_PER_COACH) {
        throw new ConflictError("that coach is full, seated and standing");
      }
      sale.standing = this._standingPrediction(trip, coachSeats, tripId, originSeq);
    }

    this._sales.push(sale);
    return this._receiptOut(sale);
  }

  async verify(reference) {
    const sale = this._sales.find((s) => s.reference === reference);
    if (!sale) throw new NotFoundError(`no booking with reference ${reference}`);
    const receipt = this._receiptOut(sale);
    return { verdict: "VALID", valid: true, ticket: receipt };
  }

  // ─── internals ──────────────────────────────────────────────────────────
  _trip(id) {
    const t = this._trips.get(id);
    if (!t) throw new NotFoundError(`no trip ${id}`);
    return t;
  }

  _requireLeg(trip, originSeq, destSeq) {
    const has = (seq) => trip.stations.some((s) => s.seq === seq);
    if (!Number.isInteger(originSeq) || !Number.isInteger(destSeq) || originSeq >= destSeq) {
      throw new ValidationError(`invalid leg [${originSeq}, ${destSeq})`);
    }
    if (!has(originSeq) || !has(destSeq)) {
      throw new ValidationError(`leg [${originSeq}, ${destSeq}) is off the route`);
    }
  }

  _activeForSeat(tripId, seatId) {
    return this._sales.filter((s) => s.trip_id === tripId && s.seat_id === seatId && s.leg);
  }

  _station(trip, seq) {
    return trip.stations.find((s) => s.seq === seq);
  }

  _stop(trip, seq) {
    return trip.stops.find((s) => s.station_seq === seq);
  }

  _fare(trip, leg, travelClass) {
    const at = (seq) => this._station(trip, seq)?.km ?? 0;
    const km = Math.max(0, at(leg.destSeq) - at(leg.originSeq));
    const mult = CLASS_MULT[travelClass] ?? 1;
    return { cents: Math.round(km * RATE_PER_KM_CENTS * mult), currency: "LKR" };
  }

  /** The seat that frees earliest after `fromSeq`, a simple stand-in for the packing sweep
   * the real backend runs (D20). */
  _standingPrediction(trip, coachSeats, tripId, fromSeq) {
    const ends = coachSeats
      .map((seat) => {
        const busy = this._activeForSeat(tripId, seat.seat_id).filter((s) => s.leg.destSeq > fromSeq);
        const freesAt = busy.length ? Math.max(...busy.map((s) => s.leg.destSeq)) : fromSeq;
        return { seat, freesAt };
      })
      .sort((a, b) => a.freesAt - b.freesAt)[0];
    return {
      after_seq: ends.freesAt,
      after_station: this._station(trip, ends.freesAt)?.name ?? "",
      seat_label: `${ends.seat.row}${ends.seat.column}`,
    };
  }

  _trainOption(trip, originCode, destCode) {
    const origin = trip.stations.find((s) => s.code === originCode);
    const dest = trip.stations.find((s) => s.code === destCode);
    if (!origin || !dest || origin.seq >= dest.seq) return null;
    const originStop = this._stop(trip, origin.seq);
    const destStop = this._stop(trip, dest.seq);
    if (!originStop?.depart || !destStop?.arrive) return null;

    const leg = { originSeq: origin.seq, destSeq: dest.seq };
    const reserved = trip.seats.filter((s) => s.coach_type === "RESERVED");
    const busy = new Set(
      reserved
        .filter((s) => this._activeForSeat(trip.trip_id, s.seat_id).some((sale) => overlaps(sale.leg, leg)))
        .map((s) => s.seat_id),
    );
    const present = new Set(reserved.map((s) => s.travel_class));
    const classes = CLASS_ORDER.filter((c) => present.has(c)).map((travelClass) => ({
      travel_class: travelClass,
      free_seats: reserved.filter((s) => s.travel_class === travelClass && !busy.has(s.seat_id)).length,
      fare: this._fare(trip, leg, travelClass),
    }));
    const km = Math.max(0, (this._station(trip, dest.seq)?.km ?? 0) - (this._station(trip, origin.seq)?.km ?? 0));

    return {
      trip_id: trip.trip_id,
      train_no: trip.train_no,
      train_name: trip.train_name,
      route_code: trip.route_code,
      service_date: trip.service_date,
      origin_seq: origin.seq,
      dest_seq: dest.seq,
      depart: originStop.depart,
      arrive: destStop.arrive,
      duration_min: minutesOf(destStop.arrive) - minutesOf(originStop.depart),
      distance_km: km,
      free_seats: classes.reduce((sum, c) => sum + c.free_seats, 0),
      from_fare: classes.reduce((min, c) => (c.fare.cents < min.cents ? c.fare : min), classes[0]?.fare ?? { cents: 0, currency: "LKR" }),
      classes,
    };
  }

  _receiptOut(sale) {
    const trip = this._trip(sale.trip_id);
    const leg = sale.leg ?? { originSeq: 0, destSeq: trip.stations.length - 1 };
    const origin = this._station(trip, leg.originSeq);
    const dest = this._station(trip, leg.destSeq);
    const originStop = this._stop(trip, leg.originSeq);
    const destStop = this._stop(trip, leg.destSeq);
    const seat = sale.seat_id ? trip.seats.find((s) => s.seat_id === sale.seat_id) : null;
    return {
      reference: sale.reference,
      qr_payload: sale.reference,
      booking_id: sale.id,
      passenger_id: sale.passenger_id,
      passenger_name: sale.passenger_name,
      trip_id: trip.trip_id,
      route_code: trip.route_code,
      train_no: trip.train_no,
      train_name: trip.train_name,
      service_date: trip.service_date,
      origin_code: origin.code,
      origin_name: origin.name,
      origin_seq: origin.seq,
      dest_code: dest.code,
      dest_name: dest.name,
      dest_seq: dest.seq,
      depart: originStop.depart,
      arrive: destStop.arrive,
      duration_min: minutesOf(destStop.arrive) - minutesOf(originStop.depart),
      travel_class: sale.travel_class,
      fare: this._fare(trip, leg, sale.travel_class),
      status: sale.status,
      issued_at: this._now,
      coach: seat?.coach ?? null,
      seat_label: seat ? `${seat.row}${seat.column}` : null,
      standing: sale.standing ?? null,
    };
  }
}
