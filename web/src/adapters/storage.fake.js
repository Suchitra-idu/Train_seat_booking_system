// L2: in-memory storage for tests. Same contract as RealStorage.

export class FakeStorage {
  constructor() {
    this._map = new Map();
  }
  get(key) {
    return this._map.has(key) ? this._map.get(key) : null;
  }
  set(key, value) {
    this._map.set(key, value);
  }
  remove(key) {
    this._map.delete(key);
  }
}
