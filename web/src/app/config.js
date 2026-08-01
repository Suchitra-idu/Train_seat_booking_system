// L4: environment wiring. The API base URL is injected at build time by Vite from
// VITE_API_BASE_URL (.env), never hardcoded in a rule (D11).
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
};
