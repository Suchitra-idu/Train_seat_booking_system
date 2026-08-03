// L2: the real ApiClient - fetch over HTTP to the FastAPI backend. Maps HTTP status to the
// port's typed errors (401→ApiError, 404→NotFoundError, 422→ValidationError,
// 429→RateLimitError) and validates every 2xx body against the OpenAPI contract (D13).
// `sell` and `verify` sit behind the shared counter key (D21); `searchTrains` is the same
// public route the traveller app uses.

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
  constructor({ baseUrl = "", counterKey = "", fetchImpl } = {}) {
    this._base = baseUrl.replace(/\/$/, "");
    this._counterKey = counterKey;
    this._fetch = fetchImpl || ((...a) => fetch(...a));
  }

  async _request(method, path, { query, body, auth = false, expect } = {}) {
    const url = this._base + path + (query ? `?${qs(query)}` : "");
    const headers = {};
    if (auth) headers["x-counter-key"] = this._counterKey;
    const init = { method, headers };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
      headers["content-type"] = "application/json";
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

  sell({ tripId, originSeq, destSeq, travelClass, passengerId, passengerName }) {
    return this._request("POST", "/admin/unreserved/sell", {
      auth: true,
      body: {
        trip_id: tripId,
        origin_seq: originSeq,
        dest_seq: destSeq,
        travel_class: travelClass,
        passenger_id: passengerId,
        passenger_name: passengerName,
      },
      expect: "sell",
    });
  }

  verify(reference) {
    return this._request("GET", `/admin/verify/${encodeURIComponent(reference)}`, {
      auth: true,
      expect: "verify",
    });
  }
}
