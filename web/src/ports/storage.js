// L1 port: small key/value storage for remembering the passenger identity and recent
// bookings across a session. Real adapter wraps localStorage; fake wraps a Map.
//
// @typedef {object} Storage
// @property {(key: string) => unknown} get
// @property {(key: string, value: unknown) => void} set
// @property {(key: string) => void} remove

export const STORAGE_KEYS = Object.freeze({
  PASSENGER: "slr.passenger",
  BOOKINGS: "slr.bookings",
});
