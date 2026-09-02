import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Ajv2020 } from "ajv/dist/2020.js";
import { validateManifest } from "../packages/kernel/src/manifest/validate.js";

const schema = JSON.parse(await readFile("docs/schema/manifest-v1.json", "utf8"));
const validate = new Ajv2020({ allErrors: true, strict: true, strictRequired: false }).compile(schema);
const base = { name: "example", kind: "module", provider: "community", version: "1.0.0", entry: "./index.js", exports: { get: [] } };

test("accepts the four module kinds", () => {
  for (const kind of ["server", "frontend", "backend", "module"]) {
    const manifest = { ...base, kind };
    assert.equal(validate(manifest), true, JSON.stringify(validate.errors)); assert.doesNotThrow(() => validateManifest(manifest));
  }
});

test("rejects unknown kinds and composition fields", () => {
  for (const manifest of [
    { ...base, kind: "unknown" },
    { ...base, composition: {} },
    { ...base, uses: ["storage"] },
    { ...base, provides: ["storage"] },
    { ...base, requires: ["storage"] },
  ]) {
    assert.equal(validate(manifest), false); assert.throws(() => validateManifest(manifest));
  }
});
