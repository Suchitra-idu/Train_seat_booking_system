// L2: the real ApiClient - fetch over HTTP to the FastAPI backend. It maps HTTP status to
// the port's typed errors (409→ConflictError, 429→RateLimitError, 422→ValidationError,
// 402→PaymentError, 404→NotFoundError) and validates every 2xx body against the OpenAPI
// contract (D13) before handing it to the UI. `fetchImpl` is injectable so the contract
// test can drive it with canned responses - no live server, no real network.

import { RESPONSE_SCHEMA, errorForStatus } from "../ports/api-client.js";
import { validateResponse } from "./schema.js";

function qs(params) {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) s.set(k, String(v));
  }
  return s.toString();
}

export class RealApiClient {
  constructor({ baseUrl = "", fetchImpl } = {}) {
    this._base = baseUrl.replace(/\/$/, "");
    this._fetch = fetchImpl || ((...a) => fetch(...a));
  }

  async _request(method, path, { query, body, headers, expect } = {}) {
    const url = this._base + path + (query ? `?${qs(query)}` : "");
    const init = { method, headers: { ...headers } };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
      init.headers["content-type"] = "application/json";
    }
    const res = await this._fetch(url, init);
    const payload = await this._parse(res);
    if (!res.ok) {
      const message = payload?.detail || payload?.error || "";
      throw errorForStatus(res.status, message, payload?.detail || "");
    }
    return expect ? validateResponse(RESPONSE_SCHEMA[expect], payload) : payload;
  }

  async _parse(res) {
    const text = await res.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }

  listTrips({ routeCode, serviceDate }) {
    return this._request("GET", "/trips", {
      query: { route_code: routeCode, service_date: serviceDate },
      expect: "listTrips",
    });
  }

  availability(tripId, { originSeq, destSeq }) {
    return this._request("GET", `/trips/${encodeURIComponent(tripId)}/availability`, {
      query: { origin_seq: originSeq, dest_seq: destSeq },
      expect: "availability",
    });
  }

  impact(tripId) {
    return this._request("GET", `/trips/${encodeURIComponent(tripId)}/impact`, {
      expect: "impact",
    });
  }

  quote({ tripId, originSeq, destSeq, travelClass }) {
    return this._request("POST", "/quote", {
      body: { trip_id: tripId, origin_seq: originSeq, dest_seq: destSeq, travel_class: travelClass },
      expect: "quote",
    });
  }

  hold({ tripId, seatId, originSeq, destSeq, passengerId, travelClass, reference }, opts = {}) {
    return this._request("POST", "/bookings/hold", {
      headers: this._idem(opts),
      body: {
        trip_id: tripId,
        seat_id: seatId,
        origin_seq: originSeq,
        dest_seq: destSeq,
        passenger_id: passengerId,
        travel_class: travelClass,
        reference: reference ?? null,
      },
      expect: "hold",
    });
  }

  unreserved({ tripId, originSeq, destSeq, passengerId, travelClass }, opts = {}) {
    return this._request("POST", "/unreserved", {
      headers: this._idem(opts),
      body: {
        trip_id: tripId,
        origin_seq: originSeq,
        dest_seq: destSeq,
        passenger_id: passengerId,
        travel_class: travelClass,
      },
      expect: "unreserved",
    });
  }

  confirm(bookingId) {
    return this._request("POST", `/bookings/${encodeURIComponent(bookingId)}/confirm`, {
      expect: "confirm",
    });
  }

  cancel(bookingId) {
    return this._request("POST", `/bookings/${encodeURIComponent(bookingId)}/cancel`, {
      expect: "cancel",
    });
  }

  lookup(reference) {
    return this._request("GET", `/bookings/${encodeURIComponent(reference)}`, {
      expect: "lookup",
    });
  }

  joinWaitlist({ tripId, originSeq, destSeq, passengerId, travelClass }) {
    return this._request("POST", "/waitlist", {
      body: {
        trip_id: tripId,
        origin_seq: originSeq,
        dest_seq: destSeq,
        passenger_id: passengerId,
        travel_class: travelClass,
      },
      expect: "joinWaitlist",
    });
  }

  _idem(opts) {
    return opts.idempotencyKey ? { "idempotency-key": opts.idempotencyKey } : {};
  }
}
