import semver from "semver";
import { STRUCTURAL_EXPORTS, type SingletonModuleKind } from "@gravewright/sdk";
import type { ActivationPlan, ModuleDefinition } from "../types.js";

/** Module kinds that require exactly one active implementation. */
export const STRUCTURAL_KINDS: readonly SingletonModuleKind[] = ["server", "frontend", "backend"];

/** Validates the active dependency graph and returns its topological order. */
export function createActivationPlan(definitions: Iterable<ModuleDefinition>): ActivationPlan {
  const all = [...definitions];
  const active = new Map(all.filter(({ state }) => state === "active").map((definition) => [definition.manifest.name, definition]));
  for (const kind of STRUCTURAL_KINDS) {
    const implementations = [...active.values()].filter(({ manifest }) => manifest.kind === kind);
    if (implementations.length !== 1) {
      const names = implementations.map(({ manifest }) => `- ${manifest.name}`).join("\n");
      throw new Error(`Expected exactly one active \`${kind}\`, found ${implementations.length}.${names ? `\n${names}` : ""}`);
    }
    const manifest = implementations[0]!.manifest;
    const exported = new Set(manifest.exports.get ?? []);
    for (const required of STRUCTURAL_EXPORTS[kind]) {
      if (!exported.has(required)) throw new Error(`Minimum contract not satisfied for ${kind}: '${required}' must be declared in exports.get`);
    }
  }
  for (const { manifest } of active.values()) {
    for (const [dependencyName, range] of Object.entries(manifest.dependencies ?? {})) {
      if (dependencyName === manifest.name) throw new Error(`Module "${manifest.name}" cannot depend on itself`);
      const dependency = active.get(dependencyName);
      if (!dependency) throw new Error(`Module "${manifest.name}" requires ${all.some(({ manifest: candidate }) => candidate.name === dependencyName) ? `dependency "${dependencyName}", but "${dependencyName}" is disabled` : `missing dependency "${dependencyName}"`}`);
      if (!semver.satisfies(dependency.manifest.version, range)) throw new Error(`Module "${manifest.name}" requires "${dependencyName}" ${range}, but ${dependency.manifest.version} is loaded`);
    }
  }
  // Depth-first traversal places each dependency before its consumers.
  const order: ModuleDefinition[] = [];
  const complete = new Set<string>(); const visiting = new Set<string>(); const trail: string[] = [];
  const visit = (name: string): void => {
    if (complete.has(name)) return;
    if (visiting.has(name)) { const start = trail.indexOf(name); throw new Error(`Circular dependency detected: ${[...trail.slice(start), name].join(" -> ")}`); }
    visiting.add(name); trail.push(name);
    const definition = active.get(name)!;
    for (const dependency of Object.keys(definition.manifest.dependencies ?? {})) visit(dependency);
    trail.pop(); visiting.delete(name); complete.add(name); order.push(definition);
  };
  for (const name of active.keys()) visit(name);
  return Object.freeze({ modules: Object.freeze(order.map(({ manifest }) => manifest.name)) });
}
