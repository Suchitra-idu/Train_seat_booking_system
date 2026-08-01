// Vendor the generated OpenAPI contract into the web tree. The backend emits
// contract/openapi.json (make emit-openapi); the real API client validates every
// response against it at runtime (D13). We copy rather than import across the repo
// boundary so the web Docker image (build context = web/) ships the schema, and a
// Vitest drift test fails the build if this copy ever falls behind the source.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../contract/openapi.json");
const dest = resolve(here, "../src/generated/openapi.json");

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`sync-contract: ${src} -> ${dest}`);
