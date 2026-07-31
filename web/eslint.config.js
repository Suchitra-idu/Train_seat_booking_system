import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

// The Dependency Rule at the source level (ARCHITECTURE.md §Enforcement): the browser's
// costly globals may appear only in adapters/. Everywhere else they must arrive through a
// port. dependency-cruiser guards the *import* graph; this guards the *global* calls it
// can't see. Layer-import rules live in .dependency-cruiser.cjs.
const COSTLY_GLOBALS = ["fetch", "EventSource", "WebSocket", "localStorage", "sessionStorage"];

export default [
  js.configs.recommended,
  ...svelte.configs["flat/recommended"],
  {
    ignores: ["dist/", "node_modules/", "coverage/"],
  },
  {
    files: ["src/**/*.{js,svelte}"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      // Browser globals exist everywhere (so no-undef stays quiet); the boundary is
      // enforced by no-restricted-globals below, not by pretending they're undefined.
      globals: globals.browser,
    },
    rules: {
      "no-restricted-globals": ["error", ...COSTLY_GLOBALS],
    },
  },
  {
    // Only adapters/ may touch the network/storage globals directly.
    files: ["src/adapters/**/*.{js,svelte}"],
    rules: { "no-restricted-globals": "off" },
  },
  {
    files: ["**/*.{test,spec}.js"],
    languageOptions: { globals: { describe: "readonly", it: "readonly", expect: "readonly" } },
    rules: { "no-restricted-globals": "off" },
  },
];
