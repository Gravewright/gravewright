import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import semver from "semver";
import { COMMON_MODULE_EXPORTS, MODULE_KINDS, MODULE_PROVIDERS, ROOM_SLOT_NAMES } from "@gravewright/sdk";

export type FindingStatus = "pass" | "warn" | "fail";
export interface Finding { status: FindingStatus; label: string; detail: string; }

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

  const manifests = new Map<string, { kind: string; version: string; dependencies: Record<string, string>; active: boolean }>();
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
        const readable = (value.exports as { get?: unknown } | undefined)?.get;
        const required = [...COMMON_MODULE_EXPORTS, ...(value.kind === "server" ? ["start", "stop", "route", "middleware", "slot"] : value.kind === "room" ? ["mount", "unmount"] : [])];
        if (!Array.isArray(readable) || required.some((name) => !readable.includes(name))) {
          throw new Error(`${String(value.kind)} exports.get must include ${required.join(", ")}`);
        }
      }
      if (value.kind === "room") {
        const slots = (value.exposes as { slots?: Array<{ name?: unknown; mounts?: unknown; contributions?: unknown }> } | undefined)?.slots;
        if (!Array.isArray(slots) || ROOM_SLOT_NAMES.some((name) => !slots.some((slot) => slot.name === name && slot.mounts === "one" && slot.contributions === "many"))) {
          throw new Error(`room exposes.slots must include the canonical room slots`);
        }
      }
      manifests.set(value.name, { kind: value.kind as string, version: value.version, dependencies: (value.dependencies as Record<string, string>) ?? {}, active: states[value.name] === "active" });
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
  for (const name of Object.keys(states)) if (!manifests.has(name)) findings.push({ status: "warn", label: "Orphan state", detail: `${name} is not installed` });
  const serverCount = [...manifests.values()].filter((item) => item.active && item.kind === "server").length;
  if (serverCount === 0) findings.push({ status: "fail", label: "Required kind", detail: "no active server module" });
  if (serverCount > 1) findings.push({ status: "fail", label: "Required kind", detail: "multiple server modules are active" });
  findings.unshift({ status: manifests.size ? "pass" : "fail", label: "Modules", detail: `${manifests.size} manifest(s) found` });
  return findings;
}
