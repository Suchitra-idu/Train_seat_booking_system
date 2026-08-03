import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

// The Dependency Rule at the source level (ARCHITECTURE.md §Enforcement): the browser's
// costly globals may appear only in adapters/. Everywhere else they must arrive through a
// port. dependency-cruiser guards the *import* graph; this guards the *global* calls it
// can't see. Layer-import rules live in .dependency-cruiser.cjs.
const COSTLY_GLOBALS = ["fetch", "localStorage", "sessionStorage", "window", "document"];

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
      globals: globals.browser,
    },
    rules: {
      "no-restricted-globals": ["error", ...COSTLY_GLOBALS],
      "no-unused-vars": ["error", { varsIgnorePattern: "^_", argsIgnorePattern: "^_" }],
    },
  },
  {
    // Only adapters/ may touch the network/DOM globals directly; app/ gets the same
    // exemption for mounting the app and injecting real adapters (main.js, App.svelte).
    files: ["src/adapters/**/*.{js,svelte}", "src/app/**/*.{js,svelte}"],
    rules: { "no-restricted-globals": "off" },
  },
  {
    files: ["**/*.{test,spec}.js"],
    languageOptions: { globals: { describe: "readonly", it: "readonly", expect: "readonly" } },
    rules: { "no-restricted-globals": "off" },
  },
];
