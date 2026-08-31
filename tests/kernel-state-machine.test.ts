import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import fc from "fast-check";
import { Kernel } from "@gravewright/kernel";

type Operation = "initialize" | "activate-a" | "activate-b" | "activate-fail" | "disable-a" | "disable-b" | "use-a" | "use-b" | "shutdown";

async function stateModule(name: string, source: string, kind: "server" | "room" | "ruleset" | "addon" = "addon"): Promise<string> {
  const root = await mkdtemp(path.join(tmpdir(), `grave-state-${name}-`));
  const exportsByKind = { server: ["start", "stop", "http", "route", "middleware"], room: ["mount", "unmount", "slots"], ruleset: [], addon: ["value"] };
  await writeFile(path.join(root, "manifest.json"), JSON.stringify({
    name, kind, provider: "community", version: "1.0.0", entry: "./index.ts",
    ...(kind === "room" ? { room_protocol: "gravewright.room/v1", exposes: { slots: ["toolbar", "main", "sidebar", "chat", "overlay", "grid"].map((name) => ({ name: `gw-${name}`, mounts: "one", contributions: "many" })) } } : {}),
    exports: { get: exportsByKind[kind] },
  }));
  await writeFile(path.join(root, "index.ts"), source);
  return root;
}

async function stateKernel(counterKey: string): Promise<Kernel> {
  const kernel = new Kernel();
  await kernel.load(await stateModule("state-server", `export default function() { return {
    http: {}, start() {}, stop() {}, route() { return () => {}; }, middleware() { return () => {}; }
  }; }`, "server"), { state: "active" });
  await kernel.load(await stateModule("state-room", `export default function() { return { mount() {}, unmount() {}, slots() { return () => {}; } }; }`, "room"), { state: "active" });
  await kernel.load(await stateModule("state-ruleset", `export default function() { return {}; }`, "ruleset"), { state: "active" });
  for (const name of ["state-a", "state-b"]) {
    await kernel.load(await stateModule(name, `export default function(ctx) {
      const state = globalThis[${JSON.stringify(counterKey)}];
      const id = ++state.created;
      ctx.onDispose(() => { if (state.disposed.has(id)) state.duplicates += 1; state.disposed.add(id); });
      return { value: ${JSON.stringify(name)} };
    }`), { state: "disabled" });
  }
  await kernel.load(await stateModule("state-fail", `export default function(ctx) {
    const state = globalThis[${JSON.stringify(counterKey)}]; const id = ++state.created;
    ctx.onDispose(() => { if (state.disposed.has(id)) state.duplicates += 1; state.disposed.add(id); });
    throw new Error("controlled factory failure");
  }`), { state: "disabled" });
  return kernel;
}

test("property: kernel lifecycle matches a state-machine model", async () => {
  await fc.assert(fc.asyncProperty(
    fc.array(fc.constantFrom<Operation>(
      "initialize", "activate-a", "activate-b", "activate-fail", "disable-a", "disable-b", "use-a", "use-b", "shutdown",
    ), { minLength: 1, maxLength: 35 }),
    async (operations) => {
      const counterKey = `__grave_state_${crypto.randomUUID().replaceAll("-", "")}`;
      const counters = { created: 0, disposed: new Set<number>(), duplicates: 0 };
      (globalThis as Record<string, unknown>)[counterKey] = counters;
      const kernel = await stateKernel(counterKey);
      const model = { initialized: false, activeA: false, activeB: false };
      try {
        for (const operation of operations) {
          if (operation === "initialize") {
            if (model.initialized) await assert.rejects(kernel.initialize(), /already initialized/);
            else { await kernel.initialize(); model.initialized = true; }
          } else if (operation === "shutdown") {
            await kernel.shutdown(); model.initialized = false;
          } else if (operation === "activate-fail") {
            if (!model.initialized) await assert.rejects(kernel.activate("state-fail"), /before kernel initialization/);
            else await assert.rejects(kernel.activate("state-fail"), /controlled factory failure/);
            assert.equal(kernel.plan().modules.includes("state-fail"), false);
            assert.throws(() => kernel.use("state-fail"), /not active/);
          } else {
            const isA = operation.endsWith("a");
            const name = isA ? "state-a" : "state-b";
            const active = isA ? model.activeA : model.activeB;
            if (operation.startsWith("activate")) {
              if (!model.initialized) await assert.rejects(kernel.activate(name), /before kernel initialization/);
              else { await kernel.activate(name); if (isA) model.activeA = true; else model.activeB = true; }
            } else if (operation.startsWith("disable")) {
              if (!model.initialized) await assert.rejects(kernel.disable(name), /before kernel initialization/);
              else { await kernel.disable(name); if (isA) model.activeA = false; else model.activeB = false; }
            } else if (model.initialized && active) {
              assert.equal(kernel.use(name).get("value"), name);
            } else assert.throws(() => kernel.use(name), /not active/);
          }

          const plan = kernel.plan();
          assert.equal(plan.modules.includes("state-a"), model.activeA);
          assert.equal(plan.modules.includes("state-b"), model.activeB);
          if (model.initialized) {
            assert.equal(Boolean(model.activeA), (() => { try { kernel.use("state-a"); return true; } catch { return false; } })());
            assert.equal(Boolean(model.activeB), (() => { try { kernel.use("state-b"); return true; } catch { return false; } })());
          }
          assert.equal(counters.duplicates, 0);
          assert.ok(counters.disposed.size <= counters.created);
        }
      } finally {
        await kernel.shutdown().catch(() => undefined);
        delete (globalThis as Record<string, unknown>)[counterKey];
      }
    },
  ), { numRuns: 20 });
});

test("queued lifecycle operations preserve their call order", async () => {
  const counterKey = `__grave_queue_${crypto.randomUUID().replaceAll("-", "")}`;
  const counters = { created: 0, disposed: new Set<number>(), duplicates: 0 };
  (globalThis as Record<string, unknown>)[counterKey] = counters;
  const kernel = await stateKernel(counterKey);
  try {
    await kernel.initialize();
    await Promise.all([kernel.activate("state-a"), kernel.disable("state-a"), kernel.activate("state-a")]);
    assert.equal(kernel.use("state-a").get("value"), "state-a");
    assert.equal(counters.duplicates, 0);
    assert.equal(counters.created, 2);
    assert.equal(counters.disposed.size, 1);
  } finally {
    await kernel.shutdown();
    delete (globalThis as Record<string, unknown>)[counterKey];
  }
});
