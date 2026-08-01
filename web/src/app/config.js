// L4: environment wiring. The API base URL is injected at build time by Vite from
// VITE_API_BASE_URL (.env), never hardcoded in a rule (D11). The demo route/date match the
// backend seed (slr/app/demo_data.py) and become a real route/date picker with P8's seed.
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  routeCode: "CMB-BAD",
  serviceDate: "2026-08-12",
};
