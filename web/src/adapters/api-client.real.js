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

  searchTrains({ originCode, destCode, serviceDate }) {
    return this._request("GET", "/search", {
      query: { origin: originCode, dest: destCode, date: serviceDate },
      expect: "searchTrains",
    });
  }

  getTrip(tripId) {
    return this._request("GET", `/trips/${encodeURIComponent(tripId)}`, {
      expect: "getTrip",
    });
  }

  availability(tripId, { originSeq, destSeq }) {
    return this._request("GET", `/trips/${encodeURIComponent(tripId)}/availability`, {
      query: { origin_seq: originSeq, dest_seq: destSeq },
      expect: "availability",
    });
  }

  quote({ tripId, originSeq, destSeq, travelClass }) {
    return this._request("POST", "/quote", {
      body: { trip_id: tripId, origin_seq: originSeq, dest_seq: destSeq, travel_class: travelClass },
      expect: "quote",
    });
  }

  hold({ tripId, seatId, originSeq, destSeq, passengerId, passengerName, reference }, opts = {}) {
    return this._request("POST", "/bookings/hold", {
      headers: this._idem(opts),
      body: {
        trip_id: tripId,
        seat_id: seatId,
        origin_seq: originSeq,
        dest_seq: destSeq,
        passenger_id: passengerId,
        passenger_name: passengerName,
        reference: reference ?? null,
      },
      expect: "hold",
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

  _idem(opts) {
    return opts.idempotencyKey ? { "idempotency-key": opts.idempotencyKey } : {};
  }
}
