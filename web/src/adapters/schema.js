// L2: runtime contract enforcement (D13). Plain JavaScript has no compiler to catch a
// FE/BE shape mismatch, so we validate every response against the OpenAPI schema the
// backend generated (vendored at src/generated/openapi.json). A drift is a thrown
// SchemaError - a red build - not a silent production bug.

import Ajv2020 from "ajv/dist/2020.js";

import openapi from "../generated/openapi.json";
import { SchemaError } from "../ports/errors.js";

const ajv = new Ajv2020({ strict: false, allErrors: true, validateFormats: false });

// Register every component under its $ref pointer so intra-schema $refs resolve.
const schemas = openapi.components?.schemas || {};
for (const [name, schema] of Object.entries(schemas)) {
  ajv.addSchema(schema, `#/components/schemas/${name}`);
}

function validatorFor(name) {
  const v = ajv.getSchema(`#/components/schemas/${name}`);
  if (!v) throw new SchemaError(`unknown contract schema '${name}'`, { schema: name });
  return v;
}

function assert(name, data) {
  const validate = validatorFor(name);
  if (!validate(data)) {
    const issues = (validate.errors || []).map((e) => `${e.instancePath || "/"} ${e.message}`);
    throw new SchemaError(`response did not match contract schema '${name}'`, {
      schema: name,
      issues,
    });
  }
  return data;
}

/**
 * Validate `data` against a named component. `array` validates each element.
 * @param {{schema: string, array?: boolean}} spec
 */
export function validateResponse(spec, data) {
  if (spec.array) {
    if (!Array.isArray(data)) {
      throw new SchemaError(`expected an array for '${spec.schema}'`, { schema: spec.schema });
    }
    data.forEach((item) => assert(spec.schema, item));
    return data;
  }
  return assert(spec.schema, data);
}

export const contractVersion = openapi.info?.version || "unknown";
