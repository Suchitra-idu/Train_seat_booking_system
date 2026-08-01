import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [svelte(), tailwindcss()],
  server: { host: true, port: 5173 },
  // Vitest must resolve Svelte's browser build so components mount under jsdom.
  resolve: process.env.VITEST ? { conditions: ["browser"] } : {},
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.{test,spec}.js"],
    setupFiles: ["./vitest.setup.js"],
  },
});
