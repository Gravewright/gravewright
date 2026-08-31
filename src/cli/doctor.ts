import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import semver from "semver";
import { MODULE_KINDS, MODULE_PROVIDERS, ROOM_PROTOCOL, ROOM_SLOT_NAMES, type ModuleKind } from "@gravewright/sdk";

export type FindingStatus = "pass" | "warn" | "fail";
export interface Finding { status: FindingStatus; label: string; detail: string; }

const REQUIRED_EXPORTS: Partial<Record<ModuleKind, string[]>> = {
  server: ["start", "stop", "http", "route", "middleware"], room: ["mount", "unmount", "slots"],
  chat: ["send", "erase"], "dice-engine": ["roll"], assets: ["store", "resolve", "mimeTypeAllowed", "remove"],
  storage: ["create", "find", "where", "update", "delete"],
};

export async function diagnose(root: string): Promise<Finding[]> {
  const findings: Finding[] = [{ status: "pass", label: "Runtime", detail: `Node.js ${process.version}` }];
  const modulesDirectory = path.join(root, "modules");
  let entries;
  try { entries = await readdir(modulesDirectory, { withFileTypes: true }); }
  catch { return [...findings, { status: "fail", label: "Modules", detail: `Directory not found: ${modulesDirectory}` }]; }

  let states: Record<string, unknown> = {};
  try {
    const parsed: unknown = JSON.parse(await readFile(path.join(root, "gravewright.modules.json"), "utf8"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("expected an object");
    states = parsed as Record<string, unknown>;
    const invalid = Object.entries(states).find(([, state]) => state !== "active" && state !== "disabled");
    if (invalid) throw new Error(`invalid state for ${invalid[0]}`);
    findings.push({ status: "pass", label: "State", detail: "gravewright.modules.json is valid" });
  } catch (error) {
    findings.push({ status: "fail", label: "State", detail: error instanceof Error ? error.message : "invalid state file" });
  }

  const manifests = new Map<string, { kind: ModuleKind; version: string; dependencies: Record<string, string>; uses: Partial<Record<ModuleKind, "required" | "optional">>; requires: Record<string, string>; provides: Record<string, string>; active: boolean }>();
  for (const entry of entries.filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
    const file = path.join(modulesDirectory, entry.name, "manifest.json");
    if (!await access(file).then(() => true, () => false)) continue;
    try {
      const value = JSON.parse(await readFile(file, "utf8")) as Record<string, unknown>;
      if (typeof value.name !== "string" || !value.name) throw new Error("name is required");
      if (manifests.has(value.name)) throw new Error(`duplicate module name ${value.name}`);
      if (!MODULE_KINDS.includes(value.kind as never)) throw new Error(`invalid kind ${String(value.kind)}`);
      if (!MODULE_PROVIDERS.includes(value.provider as never)) throw new Error(`invalid provider ${String(value.provider)}`);
      if (typeof value.version !== "string" || !semver.valid(value.version)) throw new Error("invalid SemVer version");
      if (typeof value.entry !== "string" || !await access(path.resolve(path.dirname(file), value.entry)).then(() => true, () => false)) throw new Error("entry file does not exist");
      {
        const exports = value.exports as { get?: unknown; set?: unknown; prop?: unknown } | undefined;
        if (exports?.set !== undefined || exports?.prop !== undefined) throw new Error("only exports.get is supported");
        const readable = exports?.get;
        const required = REQUIRED_EXPORTS[value.kind as ModuleKind] ?? [];
        if (!Array.isArray(readable) || required.some((name) => !readable.includes(name))) {
          throw new Error(`${String(value.kind)} exports.get must include ${required.join(", ")}`);
        }
      }
      if (value.tooling !== undefined && (!value.tooling || typeof value.tooling !== "object" || Array.isArray(value.tooling)
        || Object.entries(value.tooling).some(([name, enabled]) => !["read", "write", "stat"].includes(name) || enabled !== true))) throw new Error("invalid tooling declaration");
      if (value.uses !== undefined && (!value.uses || typeof value.uses !== "object" || Array.isArray(value.uses)
        || Object.entries(value.uses).some(([kind, mode]) => !MODULE_KINDS.includes(kind as ModuleKind) || (mode !== "required" && mode !== "optional")))) throw new Error("uses must map known kinds to required or optional");
      if (value.kind === "room") {
        if (value.room_protocol !== ROOM_PROTOCOL) throw new Error(`room_protocol must be ${ROOM_PROTOCOL}`);
        const slots = (value.exposes as { slots?: Array<{ name?: unknown; mounts?: unknown; contributions?: unknown }> } | undefined)?.slots;
        if (!Array.isArray(slots) || ROOM_SLOT_NAMES.some((name) => !slots.some((slot) => slot.name === name && slot.mounts === "one" && slot.contributions === "many"))) {
          throw new Error(`room exposes.slots must include the canonical room slots`);
        }
      }
      if (value.requires !== undefined && (!value.requires || typeof value.requires !== "object" || Array.isArray(value.requires))) throw new Error("requires must be an object");
      if (value.provides !== undefined && (!value.provides || typeof value.provides !== "object" || Array.isArray(value.provides))) throw new Error("provides must be an object");
      const requires = (value.requires as Record<string, string> | undefined) ?? {};
      const provides = (value.provides as Record<string, string> | undefined) ?? {};
      for (const [capability, range] of Object.entries(requires)) if (!capability || !semver.validRange(range)) throw new Error(`invalid required capability ${capability}`);
      for (const [capability, version] of Object.entries(provides)) if (!capability || !semver.valid(version)) throw new Error(`invalid provided capability ${capability}`);
      manifests.set(value.name, { kind: value.kind as ModuleKind, version: value.version, dependencies: (value.dependencies as Record<string, string>) ?? {}, uses: (value.uses as Partial<Record<ModuleKind, "required" | "optional">>) ?? {}, requires, provides, active: states[value.name] === "active" });
      findings.push({ status: "pass", label: "Manifest", detail: value.name });
    } catch (error) {
      findings.push({ status: "fail", label: "Manifest", detail: `${entry.name}: ${error instanceof Error ? error.message : "invalid"}` });
    }
  }
  for (const [name, manifest] of manifests) for (const [dependency, range] of Object.entries(manifest.dependencies)) {
    const target = manifests.get(dependency);
    if (!target) findings.push({ status: "fail", label: "Dependency", detail: `${name} requires missing module ${dependency}` });
    else if (manifest.active && !target.active) findings.push({ status: "fail", label: "Dependency", detail: `${name} requires disabled module ${dependency}` });
    else if (!semver.satisfies(target.version, range)) findings.push({ status: "fail", label: "Dependency", detail: `${name} requires ${dependency} ${range}, found ${target.version}` });
  }
  const providers = new Map<string, Array<{ name: string; version: string }>>();
  for (const [name, manifest] of manifests) if (manifest.active) for (const [capability, version] of Object.entries(manifest.provides)) {
    const values = providers.get(capability) ?? []; values.push({ name, version }); providers.set(capability, values);
  }
  for (const [capability, values] of providers) if (values.length > 1) findings.push({ status: "fail", label: "Capability", detail: `${capability} has multiple active providers: ${values.map(({ name }) => name).join(", ")}` });
  for (const [name, manifest] of manifests) if (manifest.active) for (const [capability, range] of Object.entries(manifest.requires)) {
    const provider = providers.get(capability)?.[0];
    if (!provider) findings.push({ status: "fail", label: "Capability", detail: `${name} requires missing capability ${capability}` });
    else if (!semver.satisfies(provider.version, range)) findings.push({ status: "fail", label: "Capability", detail: `${name} requires ${capability} ${range}, found ${provider.version}` });
  }
  for (const [name, manifest] of manifests) if (manifest.active) for (const [kind, mode] of Object.entries(manifest.uses)) {
    if (mode === "required" && ![...manifests.values()].some((candidate) => candidate.active && candidate.kind === kind)) {
      findings.push({ status: "fail", label: "Kind use", detail: `${name} requires missing kind ${kind}` });
    }
  }
  for (const name of Object.keys(states)) if (!manifests.has(name)) findings.push({ status: "warn", label: "Orphan state", detail: `${name} is not installed` });
  for (const kind of ["server", "room", "ruleset"]) {
    const count = [...manifests.values()].filter((item) => item.active && item.kind === kind).length;
    if (count === 0) findings.push({ status: "fail", label: "Required kind", detail: `no active ${kind} module` });
    if (count > 1) findings.push({ status: "fail", label: "Required kind", detail: `multiple ${kind} modules are active` });
  }
  for (const kind of ["chat", "dice-engine", "assets", "storage"]) if ([...manifests.values()].filter((item) => item.active && item.kind === kind).length > 1) findings.push({ status: "fail", label: "Kind", detail: `multiple ${kind} modules are active` });
  findings.unshift({ status: manifests.size ? "pass" : "fail", label: "Modules", detail: `${manifests.size} manifest(s) found` });
  return findings;
}
