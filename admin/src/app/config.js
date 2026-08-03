// L4: environment wiring. Neither value is hardcoded in a rule (D11); the counter key is
// a shared secret for the demo, staff login is the production upgrade (D21).
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  counterKey: import.meta.env.VITE_COUNTER_KEY || "counter-dev-key",
};
