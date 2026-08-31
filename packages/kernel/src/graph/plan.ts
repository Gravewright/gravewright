import semver from "semver";
import type { ModuleKind } from "@gravewright/sdk";
import type { ActivationPlan, ModuleDefinition } from "../types.js";

export const REQUIRED_KINDS: readonly ModuleKind[] = ["server", "room", "ruleset"];
export const SINGLETON_KINDS: readonly ModuleKind[] = ["server", "room", "ruleset", "chat", "dice-engine", "assets", "storage"];

export function createActivationPlan(definitions: Iterable<ModuleDefinition>): ActivationPlan {
  const all = [...definitions];
  const active = new Map(all.filter(({ state }) => state === "active").map((definition) => [definition.manifest.name, definition]));
  const kinds = new Map<ModuleKind, string[]>();
  for (const { manifest } of active.values()) { const names = kinds.get(manifest.kind) ?? []; names.push(manifest.name); kinds.set(manifest.kind, names); }
  for (const { manifest } of active.values()) for (const [kind, mode] of Object.entries(manifest.uses ?? {})) {
    if (mode === "required" && !(kinds.get(kind as ModuleKind)?.length)) throw new Error(`Module "${manifest.name}" requires missing kind "${kind}"`);
  }
  for (const { manifest } of active.values()) {
    for (const [dependencyName, range] of Object.entries(manifest.dependencies ?? {})) {
      if (dependencyName === manifest.name) throw new Error(`Module "${manifest.name}" cannot depend on itself`);
      const dependency = active.get(dependencyName);
      if (!dependency) throw new Error(`Module "${manifest.name}" requires ${all.some(({ manifest: candidate }) => candidate.name === dependencyName) ? `dependency "${dependencyName}", but "${dependencyName}" is disabled` : `missing dependency "${dependencyName}"`}`);
      if (!semver.satisfies(dependency.manifest.version, range)) throw new Error(`Module "${manifest.name}" requires "${dependencyName}" ${range}, but ${dependency.manifest.version} is loaded`);
    }
  }
  const capabilities: Record<string, string> = {};
  const capabilityVersions = new Map<string, string>();
  for (const { manifest } of active.values()) for (const [name, version] of Object.entries(manifest.provides ?? {})) {
    if (capabilities[name]) throw new Error(`Capability "${name}" has multiple active providers: ${capabilities[name]}, ${manifest.name}`);
    capabilities[name] = manifest.name; capabilityVersions.set(name, version);
  }
  for (const { manifest } of active.values()) for (const [name, range] of Object.entries(manifest.requires ?? {})) {
    const version = capabilityVersions.get(name);
    if (!version) throw new Error(`Module "${manifest.name}" requires missing capability "${name}"`);
    if (!semver.satisfies(version, range)) throw new Error(`Module "${manifest.name}" requires capability "${name}" ${range}, but ${version} is provided`);
  }
  const routes: Record<string, string> = {};
  for (const { manifest } of active.values()) for (const mount of Object.keys(manifest.routes ?? {})) {
    if (routes[mount]) throw new Error(`Route conflict at ${JSON.stringify(mount)} between ${routes[mount]} and ${manifest.name}`);
    routes[mount] = manifest.name;
  }
  const visualSlots = new Map<string, "one" | "many">();
  for (const { manifest } of active.values()) for (const exposure of manifest.exposes?.slots ?? []) {
    const previous = visualSlots.get(exposure.name);
    if (previous && previous !== exposure.contributions) throw new Error(`Room slot '${exposure.name}' has incompatible contribution cardinality`);
    visualSlots.set(exposure.name, exposure.contributions);
  }
  const contributionCounts = new Map<string, number>();
  const slots: Record<string, string[]> = {};
  for (const { manifest } of active.values()) for (const [slot, exports] of Object.entries(manifest.slots ?? {})) {
    slots[slot] ??= []; slots[slot].push(...exports.map((name) => `${manifest.name}.${name}`));
    if (!slot.startsWith("gw-")) continue;
    if (!visualSlots.has(slot)) throw new Error(`Module "${manifest.name}" contributes to unknown room slot '${slot}'`);
    contributionCounts.set(slot, (contributionCounts.get(slot) ?? 0) + exports.length);
  }
  for (const [slot, count] of contributionCounts) if (visualSlots.get(slot) === "one" && count > 1) throw new Error(`Room slot '${slot}' accepts only one contribution`);
  const order: ModuleDefinition[] = [];
  const complete = new Set<string>(); const visiting = new Set<string>(); const trail: string[] = [];
  const visit = (name: string): void => {
    if (complete.has(name)) return;
    if (visiting.has(name)) { const start = trail.indexOf(name); throw new Error(`Circular dependency detected: ${[...trail.slice(start), name].join(" -> ")}`); }
    visiting.add(name); trail.push(name);
    const definition = active.get(name)!;
    for (const dependency of Object.keys(definition.manifest.dependencies ?? {})) visit(dependency);
    for (const capability of Object.keys(definition.manifest.requires ?? {})) visit(capabilities[capability]!);
    for (const kind of Object.keys(definition.manifest.uses ?? {}) as ModuleKind[]) for (const provider of kinds.get(kind) ?? []) visit(provider);
    trail.pop(); visiting.delete(name); complete.add(name); order.push(definition);
  };
  for (const name of active.keys()) visit(name);
  const available = new Set([...active.values()].map(({ manifest }) => manifest.kind));
  const missing = REQUIRED_KINDS.filter((kind) => !available.has(kind));
  if (missing.length) throw new Error(`Missing active module for required kind "${missing.join("\", \"")}"`);
  for (const kind of SINGLETON_KINDS) {
    const implementations = [...active.values()].filter(({ manifest }) => manifest.kind === kind);
    if (implementations.length > 1) throw new Error(`Multiple active modules implement singleton kind "${kind}": ${implementations.map(({ manifest }) => manifest.name).join(", ")}`);
  }
  const frozenSlots = Object.fromEntries(Object.entries(slots).map(([name, values]) => [name, Object.freeze(values)]));
  const frozenKinds = Object.fromEntries([...kinds].map(([kind, names]) => [kind, Object.freeze([...names])]));
  return Object.freeze({ modules: Object.freeze(order.map(({ manifest }) => manifest.name)), capabilities: Object.freeze(capabilities), kinds: Object.freeze(frozenKinds), routes: Object.freeze(routes), slots: Object.freeze(frozenSlots) });
}
