import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// The web tree vendors the backend's generated OpenAPI (npm run sync-contract). If the
// vendored copy drifts from the source of truth, the real client would validate against a
// stale contract - so fail loudly here. Regenerate with `make emit-openapi && npm run
// sync-contract`.
describe("vendored OpenAPI contract", () => {
  it("matches the backend's generated contract/openapi.json", () => {
    const here = import.meta.dirname; // web/src/adapters
    const vendored = readFileSync(resolve(here, "../generated/openapi.json"), "utf8");
    const source = readFileSync(resolve(here, "../../../contract/openapi.json"), "utf8");
    expect(JSON.parse(vendored)).toEqual(JSON.parse(source));
  });
});
