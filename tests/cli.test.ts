import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { DiagnosticJournal } from "../src/diagnostic-journal.js";
import { scaffoldModule } from "../src/cli/scaffold.js";
import { diagnose } from "../src/cli/doctor.js";
import { buildModuleDefinition } from "../src/cli/module-build.js";
import { validateManifest } from "../packages/kernel/src/manifest/validate.js";

async function workspace(): Promise<string> {
  const root = await mkdtemp(path.join(tmpdir(), "grave-cli-"));
  await mkdir(path.join(root, "modules"));
  await writeFile(path.join(root, "package.json"), "{}\n");
  await writeFile(path.join(root, "gravewright.modules.json"), "{}\n");
  return root;
}

test("minimum scaffold creates a disabled-by-default valid module shape", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "module", name: "Fog of War" });
  assert.equal(path.basename(result.directory), "fog-of-war");
  assert.deepEqual(result.files, ["manifest.json", "package.json", "index.ts", "types.ts"]);
  const manifest = JSON.parse(await readFile(path.join(result.directory, "manifest.json"), "utf8"));
  assert.equal(manifest.kind, "module");
  assert.equal(manifest.provider, "community");
  assert.deepEqual(manifest.exports.get, []);
  const index = await readFile(path.join(result.directory, "index.ts"), "utf8");
  const types = await readFile(path.join(result.directory, "types.ts"), "utf8");
  assert.match(index, /create\(_ctx: Context\)/);
  assert.match(types, /declare module "@gravewright\/sdk"/);
  assert.match(types, /"fog-of-war": FogOfWarAPI/);
});

test("complete scaffold adds documentation, test and diagnostic example", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "module", name: "dice-tools", complete: true });
  assert.ok(result.files.includes("README.md"));
  assert.ok(result.files.includes("index.test.ts"));
  const index = await readFile(path.join(result.directory, "index.ts"), "utf8");
  assert.match(index, /create\(ctx: Context\)/);
  assert.match(index, /ctx\.diagnostic\.record/);
});

test("frontend scaffold declares its Node lifecycle", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "frontend", name: "classic-frontend" });
  const manifest = JSON.parse(await readFile(path.join(result.directory, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.exports.get, ["start", "stop"]);
});

test("scaffold accepts only the four official module kinds", async () => {
  const root = await workspace();
  for (const kind of ["campaign", "marketplace", "asset", "ui"]) {
    await assert.rejects(scaffoldModule({ root, kind, name: `old-${kind}` }), /Unknown module kind/);
  }
});

test("minimal scaffolds for every official kind build and validate", async () => {
  const root = await workspace();
  for (const kind of ["server", "frontend", "backend", "module"]) {
    const result = await scaffoldModule({ root, kind, name: `minimal-${kind}`, minimal: true });
    const manifest = JSON.parse(await readFile(path.join(result.directory, "manifest.json"), "utf8"));
    assert.doesNotThrow(() => validateManifest(manifest));
    await assert.doesNotReject(buildModuleDefinition(result.directory, { check: true }), kind);
  }
});

test("scaffold keeps optional tooling outside exports.get", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "backend", name: "observable", tooling: { read: true, stat: true } });
  const manifest = JSON.parse(await readFile(path.join(result.directory, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.tooling, { read: true, stat: true });
  assert.deepEqual(manifest.exports.get, ["start", "stop"]);
  await assert.doesNotReject(buildModuleDefinition(result.directory, { check: true }));
});

test("defineModule build reproduces scaffold artifacts and detects drift", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "module", name: "typed-module" });
  await assert.doesNotReject(buildModuleDefinition(result.directory, { check: true }));
  await writeFile(path.join(result.directory, "manifest.json"), "{}\n");
  await assert.rejects(buildModuleDefinition(result.directory, { check: true }), /manifest\.json is stale/);
  await buildModuleDefinition(result.directory);
  const manifest = JSON.parse(await readFile(path.join(result.directory, "manifest.json"), "utf8"));
  assert.equal(manifest.name, "typed-module");
});

test("diagnostic journal emits readable actions and removes unsafe fields", async () => {
  const root = await workspace();
  const file = path.join(root, "actions.txt");
  const journal = await DiagnosticJournal.create(file);
  journal.record({ event: "player.dice.roll", actor: "Elly", action: "Player roll dice", status: "success", details: { die: "d20", result: 10, userId: "secret-id" } });
  await journal.close();
  const content = await readFile(file, "utf8");
  assert.match(content, /Elly \| Player roll dice \| SUCCESS \| die=d20, result=10/);
  assert.doesNotMatch(content, /secret-id|userId/);
});

test("doctor reports missing required active module kinds", async () => {
  const findings = await diagnose(await workspace());
  assert.ok(findings.some((item) => item.status === "fail" && item.label === "Structural server"));
});

test("doctor accepts one active server, frontend and backend", async () => {
  const root = await workspace();
  const result = await scaffoldModule({ root, kind: "server", name: "http-server" });
  await scaffoldModule({ root, kind: "frontend", name: "frontend" });
  await scaffoldModule({ root, kind: "backend", name: "backend" });
  await writeFile(path.join(root, "gravewright.modules.json"), JSON.stringify({
    "http-server": "active", frontend: "active", backend: "active",
  }));
  const findings = await diagnose(root);
  assert.equal(findings.filter((item) => item.status === "fail").length, 0);
  assert.ok(findings.some((item) => item.status === "pass" && item.label === "Structural server" && item.detail === "http-server@0.1.0"));
  assert.ok(findings.some((item) => item.status === "pass" && item.label === "Structural frontend" && item.detail === "frontend@0.1.0"));
  assert.ok(findings.some((item) => item.status === "pass" && item.label === "Structural backend" && item.detail === "backend@0.1.0"));
  assert.ok(findings.some((item) => item.status === "pass" && item.label === "Modules" && item.detail === "(none)"));
  assert.equal(path.basename(result.directory), "http-server");
});
