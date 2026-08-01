// L2: browser storage over localStorage, JSON-encoded. Degrades to a no-op when storage is
// unavailable (private mode / SSR), so a booking never breaks on a storage hiccup.

export class RealStorage {
  constructor(backing) {
    this._store = backing || (typeof localStorage !== "undefined" ? localStorage : null);
  }

  get(key) {
    if (!this._store) return null;
    const raw = this._store.getItem(key);
    if (raw == null) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  set(key, value) {
    try {
      this._store?.setItem(key, JSON.stringify(value));
    } catch {
      /* quota / disabled - ignore */
    }
  }

  remove(key) {
    try {
      this._store?.removeItem(key);
    } catch {
      /* ignore */
    }
  }
}
