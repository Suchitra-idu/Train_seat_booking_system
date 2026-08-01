// L2: the in-memory ApiClient. It replicates enough of the backend to drive component
// tests with zero infrastructure - the half-open overlap invariant (so racing one seat
// yields a ConflictError), search across a timetable, quotes, and the reserved
// hold→confirm→cancel lifecycle with the D24 receipt. Outputs match the OpenAPI shapes
// exactly, and a contract test proves it (fake-conforms-to-contract), so it is a faithful
// stand-in for the real client.

import {
  ConflictError,
  NotFoundError,
  PaymentError,
  RateLimitError,
  ValidationError,
} from "../ports/errors.js";
import { DEMO_TRIP } from "./demo-trip.js";

const CLASS_MULT = { FIRST: 2.0, SECOND: 1.0, THIRD: 0.7 };
const CLASS_ORDER = ["FIRST", "SECOND", "THIRD"];
const RATE_PER_KM_CENTS = 685;
const HOLD_TTL = 900;

const overlaps = (a, b) => a.originSeq < b.destSeq && b.originSeq < a.destSeq;
const clone = (o) => JSON.parse(JSON.stringify(o));

function minutesOf(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export class FakeApiClient {
  constructor({ trips = [DEMO_TRIP], now = 1000, declinePayment = false, rateLimit = false } = {}) {
    this._trips = new Map(clone(trips).map((t) => [t.trip_id, t]));
    this._bookings = [];
    this._now = now;
    this._seq = 0;
    this._declinePayment = declinePayment;
    this._rateLimit = rateLimit;
  }

  // ─── search + reads ─────────────────────────────────────────────────────
  async searchTrains({ originCode, destCode, serviceDate }) {
    const options = [];
    for (const trip of this._trips.values()) {
      if (trip.service_date !== serviceDate) continue;
      const option = this._trainOption(trip, originCode, destCode);
      if (option) options.push(option);
    }
    return options;
  }

  async getTrip(tripId) {
    return clone(this._trip(tripId));
  }

  async availability(tripId, { originSeq, destSeq }) {
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    const leg = { originSeq, destSeq };
    const seats = trip.seats.map((s) => ({
      seat_id: s.seat_id,
      coach: s.coach,
      travel_class: s.travel_class,
      available: !this._activeForSeat(tripId, s.seat_id).some((h) => overlaps(h.leg, leg)),
    }));
    return {
      trip_id: tripId,
      origin_seq: originSeq,
      dest_seq: destSeq,
      free_count: seats.filter((s) => s.available).length,
      seats,
    };
  }

  async quote({ tripId, originSeq, destSeq, travelClass }) {
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    return {
      trip_id: tripId,
      origin_seq: originSeq,
      dest_seq: destSeq,
      travel_class: travelClass,
      fare: this._fare(trip, { originSeq, destSeq }, travelClass),
    };
  }

  // ─── reserved lifecycle ─────────────────────────────────────────────────
  async hold({ tripId, seatId, originSeq, destSeq, passengerId, passengerName, reference }) {
    this._guardRate();
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    const seat = trip.seats.find((s) => s.seat_id === seatId);
    if (!seat) throw new ValidationError(`no seat ${seatId} on this trip`);
    if (seat.coach_type !== "RESERVED") {
      throw new ValidationError(`seat ${seatId} is unreserved - sold at the counter only`);
    }
    if (reference) {
      const prior = this._bookings.find((b) => b.reference === reference);
      if (prior) return this._bookingOut(prior); // idempotent replay
    }
    const leg = { originSeq, destSeq };
    if (this._activeForSeat(tripId, seatId).some((h) => overlaps(h.leg, leg))) {
      throw new ConflictError(`seat ${seatId} is already held over that leg`);
    }
    const booking = this._add({
      trip_id: tripId,
      seat_id: seatId,
      leg,
      passenger_id: passengerId,
      passenger_name: passengerName,
      travel_class: seat.travel_class,
      status: "HELD",
      held_until: this._now + HOLD_TTL,
      fare: this._fare(trip, leg, seat.travel_class),
      reference,
    });
    return this._bookingOut(booking);
  }

  async confirm(bookingId) {
    if (this._declinePayment) throw new PaymentError();
    const b = this._byId(bookingId);
    b.status = "CONFIRMED";
    return this._receiptOut(b);
  }

  async cancel(bookingId) {
    const b = this._byId(bookingId);
    b.status = "CANCELLED";
    return this._bookingOut(b);
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

  _guardRate() {
    if (this._rateLimit) throw new RateLimitError();
  }

  _isActive(b) {
    return b.status === "HELD" || b.status === "CONFIRMED";
  }

  _activeForSeat(tripId, seatId) {
    return this._bookings.filter(
      (b) => b.trip_id === tripId && b.seat_id === seatId && this._isActive(b),
    );
  }

  _station(trip, seq) {
    return trip.stations.find((s) => s.seq === seq);
  }

  _stop(trip, seq) {
    return trip.stops.find((s) => s.station_seq === seq);
  }

  _fare(trip, leg, travelClass) {
    const km = this._legKm(trip, leg);
    const mult = CLASS_MULT[travelClass] ?? 1;
    return { cents: Math.round(km * RATE_PER_KM_CENTS * mult), currency: "LKR" };
  }

  _legKm(trip, leg) {
    const at = (seq) => this._station(trip, seq)?.km ?? 0;
    return Math.max(0, at(leg.destSeq) - at(leg.originSeq));
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
        .filter((s) => this._activeForSeat(trip.trip_id, s.seat_id).some((h) => overlaps(h.leg, leg)))
        .map((s) => s.seat_id),
    );
    const present = new Set(reserved.map((s) => s.travel_class));
    const classes = CLASS_ORDER.filter((c) => present.has(c)).map((travelClass) => ({
      travel_class: travelClass,
      free_seats: reserved.filter((s) => s.travel_class === travelClass && !busy.has(s.seat_id)).length,
      fare: this._fare(trip, leg, travelClass),
    }));

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
      distance_km: this._legKm(trip, leg),
      free_seats: classes.reduce((sum, c) => sum + c.free_seats, 0),
      from_fare: classes.reduce((min, c) => (c.fare.cents < min.cents ? c.fare : min), classes[0]?.fare ?? { cents: 0, currency: "LKR" }),
      classes,
    };
  }

  _seatLabel(seat) {
    return seat ? `${seat.row}${seat.column}` : null;
  }

  _bookingOut(b) {
    return {
      booking_id: b.booking_id,
      reference: b.reference,
      trip_id: b.trip_id,
      seat_id: b.seat_id,
      origin_seq: b.leg.originSeq,
      dest_seq: b.leg.destSeq,
      passenger_id: b.passenger_id,
      passenger_name: b.passenger_name,
      travel_class: b.travel_class,
      status: b.status,
      fare: b.fare,
      held_until: b.held_until,
      created_at: b.created_at,
    };
  }

  _receiptOut(b) {
    const trip = this._trip(b.trip_id);
    const origin = this._station(trip, b.leg.originSeq);
    const dest = this._station(trip, b.leg.destSeq);
    const originStop = this._stop(trip, b.leg.originSeq);
    const destStop = this._stop(trip, b.leg.destSeq);
    const seat = trip.seats.find((s) => s.seat_id === b.seat_id);
    return {
      reference: b.reference,
      qr_payload: b.reference,
      booking_id: b.booking_id,
      passenger_id: b.passenger_id,
      passenger_name: b.passenger_name,
      trip_id: b.trip_id,
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
      travel_class: b.travel_class,
      fare: b.fare,
      status: b.status,
      issued_at: this._now,
      coach: seat?.coach ?? null,
      seat_label: this._seatLabel(seat),
      standing: null,
    };
  }

  _add(partial) {
    const n = ++this._seq;
    const booking = {
      booking_id: `b-${n}`,
      reference: partial.reference || `SLR-${String(n).padStart(6, "0")}`,
      trip_id: partial.trip_id,
      seat_id: partial.seat_id,
      leg: partial.leg,
      passenger_id: partial.passenger_id,
      passenger_name: partial.passenger_name,
      travel_class: partial.travel_class,
      status: partial.status,
      fare: partial.fare,
      held_until: partial.held_until,
      created_at: this._now,
    };
    this._bookings.push(booking);
    return booking;
  }

  _byId(id) {
    const b = this._bookings.find((x) => x.booking_id === id);
    if (!b) throw new NotFoundError(`no booking ${id}`);
    return b;
  }
}
