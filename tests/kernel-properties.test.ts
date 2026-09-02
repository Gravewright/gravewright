import assert from "node:assert/strict";
import test from "node:test";
import fc from "fast-check";
import { createActivationPlan } from "../packages/kernel/src/graph/plan.js";
import type { ModuleDefinition } from "../packages/kernel/src/types.js";
import type { ModuleKind } from "@gravewright/sdk";

function definition(name: string, kind: ModuleKind = "module", dependencies: Record<string, string> = {}): ModuleDefinition {
  const structural = { server: ["start", "stop", "http", "route", "middleware"], frontend: ["start", "stop"], backend: ["start", "stop"], module: [] } satisfies Record<ModuleKind, string[]>;
  return { state: "active", entryPath: `/virtual/${name}/index.js`, manifest: { name, kind, provider: "community", version: "1.0.0", entry: "./index.js", dependencies, exports: { get: structural[kind] } } };
}
function base(): ModuleDefinition[] { return [definition("server", "server"), definition("frontend", "frontend"), definition("backend", "backend")]; }

test("property: dependencies precede consumers", () => fc.assert(fc.property(fc.integer({ min: 1, max: 18 }), fc.array(fc.tuple(fc.nat(30), fc.nat(30)), { maxLength: 80 }), (count, candidates) => {
  const edges = Array.from({ length: count }, () => new Set<number>());
  for (const [a, b] of candidates) { const consumer = Math.max(a % count, b % count); const dependency = Math.min(a % count, b % count); if (consumer !== dependency) edges[consumer]!.add(dependency); }
  const modules = [...base(), ...edges.map((values, index) => definition(`module-${index}`, "module", Object.fromEntries([...values].map((value) => [`module-${value}`, "^1.0.0"]))))];
  const plan = createActivationPlan(modules); const positions = new Map(plan.modules.map((name, index) => [name, index]));
  for (const item of modules) for (const dependency of Object.keys(item.manifest.dependencies ?? {})) assert.ok(positions.get(dependency)! < positions.get(item.manifest.name)!);
}), { numRuns: 60 }));

test("property: dependency cycles are rejected", () => fc.assert(fc.property(fc.integer({ min: 2, max: 15 }), (count) => {
  const modules = base();
  for (let index = 0; index < count; index += 1) modules.push(definition(`cycle-${index}`, "module", { [`cycle-${(index + 1) % count}`]: "^1.0.0" }));
  assert.throws(() => createActivationPlan(modules), /Circular dependency detected/);
}), { numRuns: 30 }));
