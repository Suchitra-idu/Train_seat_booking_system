// L0 view-core: a VerifyOut to what the inspector sees (D21, D24). Pure. "Not found" isn't
// a verdict the backend returns, a forged/mistyped reference is a 404 (D24's whole point,
// the server either has the booking or it doesn't), so the UI maps that error to the same
// shape here rather than growing a second display path.

import { receiptView } from "./receipt.js";

const TONE = {
  VALID: "success",
  UNPAID: "warning",
  CANCELLED: "error",
  EXPIRED: "error",
  NOT_FOUND: "error",
};

const LABEL = {
  VALID: "Valid",
  UNPAID: "Not paid — do not board",
  CANCELLED: "Cancelled",
  EXPIRED: "Held too long, never paid — invalid",
  NOT_FOUND: "No such ticket",
};

/** @param {{verdict: string, valid: boolean, ticket: object}} result VerifyOut */
export function verifyView(result) {
  return {
    verdict: result.verdict,
    valid: result.valid,
    tone: TONE[result.verdict] ?? "error",
    label: LABEL[result.verdict] ?? result.verdict,
    ticket: receiptView(result.ticket),
  };
}

/** The "not found" case never reaches `verifyView`, the API throws instead of returning a
 * VerifyOut, so this is the display for that path. */
export function notFoundView() {
  return { verdict: "NOT_FOUND", valid: false, tone: TONE.NOT_FOUND, label: LABEL.NOT_FOUND, ticket: null };
}
