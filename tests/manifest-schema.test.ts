import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { Ajv2020 } from "ajv/dist/2020.js";
import { validateManifest } from "../packages/kernel/src/manifest/validate.js";

const schema = JSON.parse(await readFile(path.resolve("docs/schema/manifest-v1.json"), "utf8"));
const validateSchema = new Ajv2020({ allErrors: true, strict: true, strictRequired: false }).compile(schema);

test("manifest schema v1 and runtime validator accept every shipped manifest", async () => {
  const files = [
    "modules/gravewright-server/manifest.json",
    "modules/gravewright-marketplace/manifest.json",
    ...["server", "room", "ruleset", "addon", "system"].map((kind) => `docs/minimal-templates/${kind}/manifest.json`),
  ];
  for (const file of files) {
    const manifest = JSON.parse(await readFile(path.resolve(file), "utf8"));
    assert.equal(validateSchema(manifest), true, `${file}: ${JSON.stringify(validateSchema.errors)}`);
    assert.doesNotThrow(() => validateManifest(manifest), file);
  }
});

test("manifest schema and runtime validator reject representative invalid contracts", () => {
  const valid = {
    name: "example", kind: "addon", provider: "community", version: "1.0.0",
    entry: "./index.js", exports: { get: ["read", "write", "stat"] },
  };
  for (const invalid of [
    { ...valid, version: "not-semver" },
    { ...valid, kind: "marketplace" },
    { ...valid, exports: { get: ["read", "read"] } },
    { ...valid, download_sha256: "short" },
  ]) {
    assert.equal(validateSchema(invalid), false);
    assert.throws(() => validateManifest(invalid));
  }
});
