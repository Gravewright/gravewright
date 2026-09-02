import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { Kernel } from "@gravewright/kernel";
import { type ModuleKind } from "@gravewright/sdk";

const exportsByKind: Record<ModuleKind, string[]> = {
  server: ["start", "stop", "http", "route", "middleware"],
  frontend: ["start", "stop"], backend: ["start", "stop"], module: ["value"],
};

async function fixture(name: string, kind: ModuleKind, options: { dependencies?: Record<string, string>; exports?: string[]; source?: string } = {}): Promise<string> {
  const directory = await mkdtemp(path.join(tmpdir(), "gravewright-"));
  const exported = options.exports ?? exportsByKind[kind];
  const defaults: Record<string, string> = { start: "() => undefined", stop: "() => undefined", http: "{}", route: "() => () => {}", middleware: "() => () => {}", value: "42" };
  await writeFile(path.join(directory, "manifest.json"), JSON.stringify({ name, kind, provider: "community", version: "1.0.0", entry: "./index.ts", ...(options.dependencies ? { dependencies: options.dependencies } : {}), exports: { get: exported } }));
  await writeFile(path.join(directory, "index.ts"), options.source ?? `export default function() { return { ${exported.map((key) => `${JSON.stringify(key)}: ${defaults[key] ?? "undefined"}`).join(",")} }; }`);
  return directory;
}

async function loadBase(kernel: Kernel): Promise<void> {
  await kernel.load(await fixture("server", "server"), { state: "active" });
  await kernel.load(await fixture("frontend", "frontend"), { state: "active" });
  await kernel.load(await fixture("backend", "backend", { dependencies: { server: "^1.0.0" } }), { state: "active" });
}

test("requires exactly one server, frontend and backend", async () => {
  for (const missing of ["server", "frontend", "backend"] as const) {
    const kernel = new Kernel();
    for (const kind of ["server", "frontend", "backend"] as const) if (kind !== missing) await kernel.load(await fixture(kind, kind), { state: "active" });
    assert.throws(() => kernel.plan(), new RegExp("Expected exactly one active `" + missing + "`, found 0"));
  }
});

for (const kind of ["server", "frontend", "backend"] as const) test(`rejects two active ${kind} implementations with their names`, async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture(`second-${kind}`, kind), { state: "active" });
  assert.throws(() => kernel.plan(), new RegExp("Expected exactly one active `" + kind + "`, found 2[\\s\\S]*" + kind + "[\\s\\S]*second-" + kind));
});

test("rejects a second structural implementation and allows many modules", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture("other-frontend", "frontend"), { state: "active" });
  assert.throws(() => kernel.plan(), /Expected exactly one active `frontend`, found 2/);
  const modules = new Kernel(); await loadBase(modules);
  await modules.load(await fixture("one", "module"), { state: "active" }); await modules.load(await fixture("two", "module"), { state: "active" });
  assert.doesNotThrow(() => modules.plan());
});

test("ctx.use only resolves declared concrete dependencies and get only exposes manifest exports", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture("library", "module"), { state: "active" });
  await kernel.load(await fixture("consumer", "module", { dependencies: { library: "^1.0.0" }, exports: ["read"], source: `export default function(ctx) { const library = ctx.use("library"); return { read: () => library.get("value") }; }` }), { state: "active" });
  await kernel.initialize();
  assert.equal((kernel.use("consumer").get("read") as () => number)(), 42);
  assert.throws(() => kernel.use("library").get("internal"), /cannot access export "internal" from module "library"/);
  await kernel.shutdown();
});

test("context exposes only concrete use, lifecycle and diagnostics", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture("context", "module", { exports: ["keys"], source: `export default function(ctx) { return { keys: Object.keys(ctx).sort() }; }` }), { state: "active" });
  await kernel.initialize();
  assert.deepEqual(kernel.use("context").get("keys"), ["diagnostic", "onDispose", "use"]);
  await kernel.shutdown();
});

for (const kind of ["server", "frontend", "backend"] as const) test(`${kind} enforces its minimum contract`, async () => {
  const kernel = new Kernel();
  for (const current of ["server", "frontend", "backend"] as const) await kernel.load(await fixture(current, current, current === kind ? { exports: exportsByKind[current].slice(1) } : {}), { state: "active" });
  await assert.rejects(kernel.initialize(), new RegExp(`Minimum contract not satisfied for ${kind}`));
});

test("server realtime is transport-neutral and optional", async () => {
  const kernel = new Kernel();
  const serverExports = [...exportsByKind.server, "realtime"];
  await kernel.load(await fixture("server", "server", { exports: serverExports, source: `export default function() { return { start() {}, stop() {}, http: {}, route() { return () => {}; }, middleware() { return () => {}; }, realtime: { toRoom() {}, toGM() {}, toWhisper() {} } }; }` }), { state: "active" });
  await kernel.load(await fixture("frontend", "frontend"), { state: "active" }); await kernel.load(await fixture("backend", "backend"), { state: "active" });
  await kernel.initialize();
  const realtime = kernel.use("server").get("realtime") as { toRoom(room: string, message: unknown): void };
  assert.doesNotThrow(() => realtime.toRoom("room", { type: "scene.updated", payload: {} }));
  await kernel.shutdown();
});

test("undeclared and transitive dependencies do not grant ctx.use access", async () => {
  const undeclared = new Kernel(); await loadBase(undeclared);
  await undeclared.load(await fixture("library", "module"), { state: "active" });
  await undeclared.load(await fixture("consumer", "module", { source: `export default function(ctx) { ctx.use("library"); return { value: 1 }; }` }), { state: "active" });
  await assert.rejects(undeclared.initialize(), /Module "consumer" cannot use undeclared dependency "library"/);

  const transitive = new Kernel(); await loadBase(transitive);
  await transitive.load(await fixture("c", "module"), { state: "active" });
  await transitive.load(await fixture("b", "module", { dependencies: { c: "^1.0.0" } }), { state: "active" });
  await transitive.load(await fixture("a", "module", { dependencies: { b: "^1.0.0" }, source: `export default function(ctx) { ctx.use("c"); return { value: 1 }; }` }), { state: "active" });
  await assert.rejects(transitive.initialize(), /Module "a" cannot use undeclared dependency "c"/);
});

test("missing, disabled and incompatible dependencies identify consumer and dependency", async () => {
  const missing = new Kernel(); await loadBase(missing);
  await missing.load(await fixture("consumer", "module", { dependencies: { absent: "^1.0.0" } }), { state: "active" });
  assert.throws(() => missing.plan(), /Module "consumer" requires missing dependency "absent"/);

  const disabled = new Kernel(); await loadBase(disabled);
  await disabled.load(await fixture("library", "module"), { state: "disabled" });
  await disabled.load(await fixture("consumer", "module", { dependencies: { library: "^1.0.0" } }), { state: "active" });
  assert.throws(() => disabled.plan(), /Module "consumer" requires dependency "library", but "library" is disabled/);

  const incompatible = new Kernel(); await loadBase(incompatible);
  await incompatible.load(await fixture("library", "module"), { state: "active" });
  await incompatible.load(await fixture("consumer", "module", { dependencies: { library: "^2.0.0" } }), { state: "active" });
  assert.throws(() => incompatible.plan(), /Module "consumer" requires "library" \^2\.0\.0, but 1\.0\.0 is loaded/);
});

test("get denial identifies consumer, provider, requested export and public exports", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture("scenes", "module", { exports: ["find", "create"] }), { state: "active" });
  await kernel.load(await fixture("map", "module", { dependencies: { scenes: "^1.0.0" }, exports: ["read"], source: `export default function(ctx) { const scenes = ctx.use("scenes"); return { read: () => scenes.get("repository") }; }` }), { state: "active" });
  await kernel.initialize();
  assert.throws(() => (kernel.use("map").get("read") as () => unknown)(), (error: unknown) => {
    assert.ok(error instanceof Error); assert.match(error.message, /Module "map"/); assert.match(error.message, /module "scenes"/); assert.match(error.message, /Requested export: repository/); assert.match(error.message, /Public exports: create, find/); return true;
  });
  await kernel.shutdown();
});

test("activation failure rolls back onDispose resources exactly once", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  globalThis.__gravewrightCleanupCount = 0;
  await kernel.load(await fixture("failing", "module", { source: `export default function(ctx) { ctx.onDispose(() => { globalThis.__gravewrightCleanupCount += 1; }); throw new Error("activation failed"); }` }), { state: "disabled" });
  await kernel.initialize();
  await assert.rejects(kernel.activate("failing"), /activation failed/);
  assert.equal(globalThis.__gravewrightCleanupCount, 1);
  await kernel.shutdown();
  assert.equal(globalThis.__gravewrightCleanupCount, 1);
  delete globalThis.__gravewrightCleanupCount;
});

test("shutdown stops structural lifecycles and disposes resources in reverse order once", async () => {
  globalThis.__gravewrightEvents = [];
  const kernel = new Kernel();
  const structural = (name: string, kind: "server" | "frontend" | "backend", extra = "") => fixture(name, kind, { source: `export default function(ctx) { ctx.onDispose(() => globalThis.__gravewrightEvents.push("dispose:${name}")); return { start() { globalThis.__gravewrightEvents.push("start:${name}"); }, stop() { globalThis.__gravewrightEvents.push("stop:${name}"); }${extra} }; }` });
  await kernel.load(await structural("server", "server", `, http: {}, route() { return () => {}; }, middleware() { return () => {}; }`), { state: "active" });
  await kernel.load(await structural("frontend", "frontend"), { state: "active" });
  await kernel.load(await structural("backend", "backend"), { state: "active" });
  await kernel.load(await fixture("leaf", "module", { source: `export default function(ctx) { ctx.onDispose(() => globalThis.__gravewrightEvents.push("dispose:leaf")); return { value: 1 }; }` }), { state: "active" });
  await kernel.initialize(); await kernel.shutdown(); await kernel.shutdown();
  assert.deepEqual(globalThis.__gravewrightEvents, ["start:backend", "start:frontend", "start:server", "stop:server", "stop:frontend", "stop:backend", "dispose:leaf", "dispose:backend", "dispose:frontend", "dispose:server"]);
  delete globalThis.__gravewrightEvents;
});

test("hot activation and disable are restricted to module", async () => {
  const kernel = new Kernel(); await loadBase(kernel);
  await kernel.load(await fixture("feature", "module"), { state: "disabled" });
  await kernel.initialize();
  for (const name of ["server", "frontend", "backend"]) {
    await assert.rejects(kernel.activate(name), new RegExp(`Structural implementation "${name}" cannot be activated`));
    await assert.rejects(kernel.disable(name), new RegExp(`Structural implementation "${name}" cannot be disabled`));
  }
  await kernel.activate("feature"); assert.equal(kernel.use("feature").get("value"), 42);
  await kernel.disable("feature"); assert.throws(() => kernel.use("feature"), /not active/);
  await kernel.shutdown();
});

test("Node kernel has no DOM or browser frontend lifecycle dependency", async () => {
  const source = await readFile(new URL("../packages/kernel/src/kernel.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /HTMLElement|\.get\("mount"\)|\.get\("unmount"\)/);
});

declare global {
  var __gravewrightCleanupCount: number | undefined;
  var __gravewrightEvents: string[] | undefined;
}
