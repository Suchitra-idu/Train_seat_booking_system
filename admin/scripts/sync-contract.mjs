// Vendor the generated OpenAPI contract into the admin tree, same convention as web/
// (see web/scripts/sync-contract.mjs). The backend emits contract/openapi.json
// (make emit-openapi); the real API client validates every response against it at
// runtime (D13).
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../contract/openapi.json");
const dest = resolve(here, "../src/generated/openapi.json");

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`sync-contract: ${src} -> ${dest}`);
