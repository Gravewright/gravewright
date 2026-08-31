import assert from "node:assert/strict";
import test from "node:test";
import fc from "fast-check";
import { createActivationPlan } from "../packages/kernel/src/graph/plan.js";
import type { ModuleDefinition } from "../packages/kernel/src/types.js";
import type { ModuleManifest } from "@gravewright/sdk";

function definition(name: string, dependencies: Record<string, string> = {}, extra: Partial<ModuleManifest> = {}): ModuleDefinition {
  return {
    state: "active",
    entryPath: `/virtual/${name}/index.js`,
    manifest: {
      name, kind: name === "server" ? "server" : "addon", provider: "community",
      version: "1.0.0", entry: "./index.js", dependencies, exports: { get: [] }, ...extra,
    },
  };
}

function requiredDefinitions(): ModuleDefinition[] {
  return [
    definition("server", {}, { kind: "server" }),
    definition("room", {}, { kind: "room" }),
    definition("ruleset", {}, { kind: "ruleset" }),
  ];
}

test("property: every generated DAG plans dependencies before consumers", () => {
  fc.assert(fc.property(
    fc.integer({ min: 1, max: 18 }),
    fc.array(fc.tuple(fc.nat(30), fc.nat(30)), { maxLength: 80 }),
    (count, candidates) => {
      const dependencies = Array.from({ length: count }, () => new Set<number>());
      for (const [left, right] of candidates) {
        const consumer = Math.max(left % count, right % count);
        const dependency = Math.min(left % count, right % count);
        if (consumer !== dependency) dependencies[consumer]!.add(dependency);
      }
      const modules = [...requiredDefinitions(), ...dependencies.map((items, index) => definition(
        `module-${index}`,
        Object.fromEntries([...items].map((dependency) => [`module-${dependency}`, "^1.0.0"])),
      ))];
      const plan = createActivationPlan(modules);
      const positions = new Map(plan.modules.map((name, index) => [name, index]));
      for (const item of modules) for (const dependency of Object.keys(item.manifest.dependencies ?? {})) {
        assert.ok(positions.get(dependency)! < positions.get(item.manifest.name)!);
      }
    },
  ), { numRuns: 60 });
});

test("property: generated dependency cycles are always rejected", () => {
  fc.assert(fc.property(fc.integer({ min: 2, max: 15 }), (count) => {
    const modules = requiredDefinitions();
    for (let index = 0; index < count; index += 1) {
      modules.push(definition(`cycle-${index}`, { [`cycle-${(index + 1) % count}`]: "^1.0.0" }));
    }
    assert.throws(() => createActivationPlan(modules), /Circular dependency detected/);
  }), { numRuns: 30 });
});

test("property: compatible capability ranges plan and incompatible ranges fail", () => {
  fc.assert(fc.property(
    fc.integer({ min: 0, max: 20 }), fc.integer({ min: 0, max: 20 }),
    (major, minor) => {
      const version = `${major}.${minor}.0`;
      const provider = definition("provider", {}, { provides: { renderer: version } });
      assert.doesNotThrow(() => createActivationPlan([
        ...requiredDefinitions(), provider, definition("consumer", {}, { requires: { renderer: version } }),
      ]));
      assert.throws(() => createActivationPlan([
        ...requiredDefinitions(), provider, definition("consumer", {}, { requires: { renderer: `${major + 1}.0.0` } }),
      ]), /requires capability/);
    },
  ), { numRuns: 40 });
});

test("property: disabling generated leaf modules preserves graph invariants", () => {
  fc.assert(fc.property(fc.integer({ min: 1, max: 20 }), (count) => {
    const modules = requiredDefinitions();
    for (let index = 0; index < count; index += 1) {
      modules.push(definition(`chain-${index}`, index === 0 ? {} : { [`chain-${index - 1}`]: "^1.0.0" }));
    }
    const leaf = modules.at(-1)!;
    assert.equal(createActivationPlan(modules).modules.includes(leaf.manifest.name), true);
    leaf.state = "disabled";
    const disabled = createActivationPlan(modules);
    assert.equal(disabled.modules.includes(leaf.manifest.name), false);
    leaf.state = "active";
    assert.equal(createActivationPlan(modules).modules.includes(leaf.manifest.name), true);
  }), { numRuns: 30 });
});
