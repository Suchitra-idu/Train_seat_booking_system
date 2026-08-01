// L2: the in-memory ApiClient. It replicates enough of the backend to drive component
// tests with zero infrastructure - the half-open overlap invariant (so racing one seat
// yields a ConflictError), quotes, the reserved hold→confirm→cancel lifecycle with waitlist
// promotion, and the unreserved NIC-only PENDING flow. Outputs match the OpenAPI shapes
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
const RATE_PER_KM_CENTS = 685;
const HOLD_TTL = 900;

const overlaps = (a, b) => a.originSeq < b.destSeq && b.originSeq < a.destSeq;
const clone = (o) => JSON.parse(JSON.stringify(o));
// A booking as the wire sees it: drop the internal leg helper, keep origin/dest_seq.
const out = (b) => {
  const c = clone(b);
  delete c.leg;
  return c;
};

export class FakeApiClient {
  constructor({ trips = [DEMO_TRIP], now = 1000, declinePayment = false, rateLimit = false } = {}) {
    this._trips = new Map(clone(trips).map((t) => [t.trip_id, t]));
    this._bookings = [];
    this._waitlist = [];
    this._now = now;
    this._seq = 0;
    this._declinePayment = declinePayment;
    this._rateLimit = rateLimit;
  }

  // ─── reads ──────────────────────────────────────────────────────────────
  async listTrips({ routeCode, serviceDate }) {
    return [...this._trips.values()]
      .filter((t) => t.route_code === routeCode && t.service_date === serviceDate)
      .map(clone);
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

  async impact(tripId) {
    const trip = this._trip(tripId);
    const active = this._bookings.filter((b) => b.trip_id === tripId && this._isActive(b));
    const fullKm = trip.stations[trip.stations.length - 1].km - trip.stations[0].km;
    const usedKm = active.reduce((sum, b) => sum + this._legKm(trip, b.leg), 0);
    return {
      trip_id: tripId,
      active_legs: active.length,
      seats_used: new Set(active.map((b) => b.seat_id)).size,
      seat_km_reclaimed: Math.max(0, active.length * fullKm - usedKm),
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
  async hold({ tripId, seatId, originSeq, destSeq, passengerId, travelClass, reference }) {
    this._guardRate();
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    const seat = trip.seats.find((s) => s.seat_id === seatId);
    if (!seat) throw new ValidationError(`no seat ${seatId} on this trip`);
    if (seat.coach_type !== "RESERVED") {
      throw new ValidationError(`seat ${seatId} is unreserved - book it via the NIC flow`);
    }
    if (reference) {
      const prior = this._bookings.find((b) => b.reference === reference);
      if (prior) return out(prior); // idempotent replay
    }
    const leg = { originSeq, destSeq };
    if (this._activeForSeat(tripId, seatId).some((h) => overlaps(h.leg, leg))) {
      throw new ConflictError(`seat ${seatId} is already held over that leg`);
    }
    return out(
      this._add({
        trip_id: tripId,
        seat_id: seatId,
        leg,
        passenger_id: passengerId,
        travel_class: travelClass,
        status: "HELD",
        held_until: this._now + HOLD_TTL,
        reference,
      }),
    );
  }

  async unreserved({ tripId, originSeq, destSeq, passengerId, travelClass }) {
    this._guardRate();
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    return out(
      this._add({
        trip_id: tripId,
        seat_id: "",
        leg: { originSeq, destSeq },
        passenger_id: passengerId,
        travel_class: travelClass,
        status: "PENDING",
        held_until: 0,
      }),
    );
  }

  async confirm(bookingId) {
    if (this._declinePayment) throw new PaymentError();
    const b = this._byId(bookingId);
    b.status = "CONFIRMED";
    return out(b);
  }

  async cancel(bookingId) {
    const b = this._byId(bookingId);
    b.status = "CANCELLED";
    const promoted = this._promote(b);
    return { cancelled: out(b), promoted: promoted ? out(promoted) : null };
  }

  async lookup(reference) {
    const b = this._bookings.find((x) => x.reference === reference);
    if (!b) throw new NotFoundError(`no booking ${reference}`);
    return out(b);
  }

  async joinWaitlist({ tripId, originSeq, destSeq, passengerId, travelClass }) {
    const trip = this._trip(tripId);
    this._requireLeg(trip, originSeq, destSeq);
    const entry = {
      waitlist_id: `wl-${++this._seq}`,
      trip_id: tripId,
      origin_seq: originSeq,
      dest_seq: destSeq,
      leg: { originSeq, destSeq },
      passenger_id: passengerId,
      travel_class: travelClass,
      created_at: this._now,
    };
    this._waitlist.push(entry);
    const { leg, ...wire } = entry;
    void leg;
    return clone(wire);
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

  _fare(trip, leg, travelClass) {
    const km = this._legKm(trip, leg);
    const mult = CLASS_MULT[travelClass] ?? 1;
    return { cents: Math.round(km * RATE_PER_KM_CENTS * mult), currency: "LKR" };
  }

  _legKm(trip, leg) {
    const at = (seq) => trip.stations.find((s) => s.seq === seq)?.km ?? 0;
    return Math.max(0, at(leg.destSeq) - at(leg.originSeq));
  }

  _add(partial) {
    const n = ++this._seq;
    const booking = {
      booking_id: `b-${n}`,
      reference: partial.reference || `SLR-${String(n).padStart(6, "0")}`,
      trip_id: partial.trip_id,
      seat_id: partial.seat_id,
      leg: partial.leg,
      origin_seq: partial.leg.originSeq,
      dest_seq: partial.leg.destSeq,
      passenger_id: partial.passenger_id,
      travel_class: partial.travel_class,
      status: partial.status,
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

  /** FIFO promotion of the oldest compatible waiter onto a freed seat/leg (D16). */
  _promote(cancelled) {
    const idx = this._waitlist.findIndex(
      (w) =>
        w.trip_id === cancelled.trip_id &&
        w.travel_class === cancelled.travel_class &&
        w.leg.originSeq >= cancelled.leg.originSeq &&
        w.leg.destSeq <= cancelled.leg.destSeq &&
        !this._activeForSeat(cancelled.trip_id, cancelled.seat_id).some((h) =>
          overlaps(h.leg, w.leg),
        ),
    );
    if (idx === -1) return null;
    const [w] = this._waitlist.splice(idx, 1);
    return this._add({
      trip_id: w.trip_id,
      seat_id: cancelled.seat_id,
      leg: w.leg,
      passenger_id: w.passenger_id,
      travel_class: w.travel_class,
      status: "HELD",
      held_until: this._now + HOLD_TTL,
    });
  }
}
