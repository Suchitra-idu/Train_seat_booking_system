// The Dependency Rule for the frontend hexagon (ARCHITECTURE.md §Frontend).
// Imports point inward only:  app > ui > adapters > ports > view-core.
// Layer imports are guarded here; the costly *globals* (fetch/EventSource/localStorage)
// are guarded by eslint.config.js. Run: `depcruise src --config .dependency-cruiser.cjs`.

/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "view-core-is-pure",
      comment: "L0 view-core is pure — no framework, no ports, no adapters, no UI.",
      severity: "error",
      from: { path: "^src/view-core/" },
      to: { path: "^(src/(ports|adapters|ui|app)/|node_modules/svelte)" },
    },
    {
      name: "ports-see-only-view-core",
      comment: "L1 ports depend on view-core only — never an implementation.",
      severity: "error",
      from: { path: "^src/ports/" },
      to: { path: "^src/(adapters|ui|app)/" },
    },
    {
      name: "ui-never-imports-adapters",
      comment: "L3 ui talks to ports, never a concrete adapter (use the fake in tests).",
      severity: "error",
      from: { path: "^src/ui/" },
      to: { path: "^src/(adapters|app)/" },
    },
    {
      name: "adapters-dont-drive-ui",
      comment: "L2 adapters implement ports; they don't reach up into ui or app.",
      severity: "error",
      from: { path: "^src/adapters/" },
      to: { path: "^src/(ui|app)/" },
    },
    {
      name: "no-orphans",
      comment: "Dead module — unreferenced and not an entry point.",
      severity: "warn",
      from: { orphan: true, pathNot: ["\\.(test|spec)\\.js$", "\\.d\\.ts$"] },
      to: {},
    },
    {
      name: "no-circular",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: false,
    enhancedResolveOptions: {
      extensions: [".js", ".svelte"],
    },
  },
};
