import semver from "semver";
import {
  MODULE_KINDS,
  MODULE_PROVIDERS,
  ROOM_PROTOCOL,
  ROOM_SLOT_NAMES,
  type ModuleKind,
  type ModuleManifest,
  type SlotExposure,
} from "@gravewright/sdk";

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringArray(value: unknown, field: string): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item)) {
    throw new Error(`Invalid manifest: ${field} must be an array of non-empty strings`);
  }
  return value as string[];
}

function versionMap(value: unknown, field: string, ranges: boolean): Record<string, string> | undefined {
  if (value === undefined) return undefined;
  if (!isObject(value)) throw new Error(`Invalid manifest: ${field} must be an object`);
  const result: Record<string, string> = {};
  for (const [name, version] of Object.entries(value)) {
    if (!/^[a-z0-9]+(?:[.-][a-z0-9]+)*$/.test(name) || typeof version !== "string"
      || (ranges ? semver.validRange(version) === null : semver.valid(version) === null)) {
      throw new Error(`Invalid manifest: ${field} '${name}' has invalid ${ranges ? "SemVer range" : "version"} '${String(version)}'`);
    }
    result[name] = version;
  }
  return result;
}

function slotExposures(value: unknown, kind: ModuleKind): { slots: SlotExposure[] } | undefined {
  if (value === undefined) {
    if (kind === "room") throw new Error("Invalid manifest: room must declare exposes.slots");
    return undefined;
  }
  if (!isObject(value) || !Array.isArray(value.slots)) {
    throw new Error("Invalid manifest: exposes.slots must be an array");
  }
  if (kind !== "room") throw new Error("Invalid manifest: only room modules may declare exposes.slots");
  const slots: SlotExposure[] = [];
  const names = new Set<string>();
  for (const item of value.slots) {
    if (!isObject(item) || typeof item.name !== "string" || !/^gw-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item.name)) {
      throw new Error("Invalid manifest: exposed slot names must use gw-kebab-case");
    }
    if (names.has(item.name)) throw new Error(`Invalid manifest: duplicate exposed slot '${item.name}'`);
    if (item.mounts !== "one") throw new Error(`Invalid manifest: exposed slot '${item.name}' must use mounts "one"`);
    if (item.contributions !== "one" && item.contributions !== "many") {
      throw new Error(`Invalid manifest: exposed slot '${item.name}' has invalid contribution cardinality`);
    }
    names.add(item.name);
    slots.push({ name: item.name, mounts: "one", contributions: item.contributions });
  }
  if (kind === "room") {
    for (const name of ROOM_SLOT_NAMES) {
      const slot = slots.find((candidate) => candidate.name === name);
      if (!slot) throw new Error(`Invalid manifest: room must expose required slot '${name}'`);
      if (slot.contributions !== "many") {
        throw new Error(`Invalid manifest: required room slot '${name}' must accept many contributions`);
      }
    }
  }
  return { slots };
}

export function validateManifest(value: unknown): ModuleManifest {
  if (!isObject(value)) throw new Error("Invalid manifest: expected an object");
  for (const field of ["name", "version", "entry"] as const) {
    if (typeof value[field] !== "string" || value[field].length === 0) {
      throw new Error(`Invalid manifest: ${field} must be a non-empty string`);
    }
  }
  if (!MODULE_KINDS.includes(value.kind as ModuleKind)) {
    throw new Error(`Invalid kind: ${String(value.kind)}`);
  }
  if (!MODULE_PROVIDERS.includes(value.provider as ModuleManifest["provider"])) {
    throw new Error(`Invalid provider: ${String(value.provider)}`);
  }
  if (!isObject(value.exports)) throw new Error("Invalid manifest: exports must be an object");
  if (value.exports.set !== undefined || value.exports.prop !== undefined) {
    throw new Error("Invalid manifest: only exports.get is supported");
  }
  if (!semver.valid(value.version as string)) {
    throw new Error(`Invalid manifest: version '${String(value.version)}' is not valid SemVer`);
  }

  let dependencies: Record<string, string> | undefined;
  if (value.dependencies !== undefined) {
    if (!isObject(value.dependencies)) {
      throw new Error("Invalid manifest: dependencies must be an object");
    }
    dependencies = {};
    for (const [name, range] of Object.entries(value.dependencies)) {
      if (!name || typeof range !== "string" || semver.validRange(range) === null) {
        throw new Error(`Invalid manifest: dependency '${name}' has invalid SemVer range '${String(range)}'`);
      }
      dependencies[name] = range;
    }
  }
  const exposes = slotExposures(value.exposes, value.kind as ModuleKind);
  const requires = versionMap(value.requires, "requires", true);
  const provides = versionMap(value.provides, "provides", false);
  if (value.kind === "room" && value.room_protocol !== ROOM_PROTOCOL) {
    throw new Error(`Invalid manifest: room_protocol must be '${ROOM_PROTOCOL}'`);
  }
  if (value.kind !== "room" && value.room_protocol !== undefined) {
    throw new Error("Invalid manifest: only room modules may declare room_protocol");
  }

  let routes: Record<string, string> | undefined;
  if (value.routes !== undefined) {
    if (!isObject(value.routes)) throw new Error("Invalid manifest: routes must be an object");
    routes = {};
    for (const [mount, exportName] of Object.entries(value.routes)) {
      if (!mount) throw new Error("Invalid manifest: route mounts must be non-empty strings");
      if (typeof exportName !== "string" || !exportName) {
        throw new Error(`Invalid manifest: route export for mount '${mount}' must be a non-empty string`);
      }
      routes[mount] = exportName;
    }
  }
  let middleware: Record<string, string[]> | undefined;
  if (value.middleware !== undefined) {
    if (!isObject(value.middleware)) throw new Error("Invalid manifest: middleware must be an object");
    middleware = {};
    for (const [mount, exports] of Object.entries(value.middleware)) {
      if (!mount) throw new Error("Invalid manifest: middleware mounts must be non-empty strings");
      const names = stringArray(exports, `middleware.${mount}`)!;
      if (new Set(names).size !== names.length) {
        throw new Error(`Invalid manifest: middleware mount '${mount}' must not contain duplicate names`);
      }
      middleware[mount] = names;
    }
  }
  let slots: Record<string, string[]> | undefined;
  if (value.slots !== undefined) {
    if (!isObject(value.slots)) throw new Error("Invalid manifest: slots must be an object");
    slots = {};
    for (const [slotName, exports] of Object.entries(value.slots)) {
      if (!slotName) throw new Error("Invalid manifest: slot names must be non-empty strings");
      const names = stringArray(exports, `slots.${slotName}`)!;
      if (new Set(names).size !== names.length) {
        throw new Error(`Invalid manifest: slot '${slotName}' must not contain duplicate names`);
      }
      slots[slotName] = names;
    }
  }

  const manifest = {
    name: value.name,
    kind: value.kind,
    provider: value.provider,
    version: value.version,
    entry: value.entry,
    ...(value.types === undefined ? {} : { types: value.types }),
    ...(dependencies === undefined ? {} : { dependencies }),
    ...(requires === undefined ? {} : { requires }),
    ...(provides === undefined ? {} : { provides }),
    ...(value.room_protocol === undefined ? {} : { room_protocol: value.room_protocol }),
    ...(exposes === undefined ? {} : { exposes }),
    ...(routes === undefined ? {} : { routes }),
    ...(middleware === undefined ? {} : { middleware }),
    ...(slots === undefined ? {} : { slots }),
    exports: {
      get: stringArray(value.exports.get, "exports.get"),
    },
    ...(value.manifest_url === undefined ? {} : { manifest_url: value.manifest_url }),
    ...(value.download_url === undefined ? {} : { download_url: value.download_url }),
    ...(value.download_sha256 === undefined ? {} : { download_sha256: value.download_sha256 }),
  } as ModuleManifest;

  if (manifest.manifest_url !== undefined && typeof manifest.manifest_url !== "string") {
    throw new Error("Invalid manifest: manifest_url must be a string");
  }
  if (manifest.download_url !== undefined && typeof manifest.download_url !== "string") {
    throw new Error("Invalid manifest: download_url must be a string");
  }
  if (manifest.download_sha256 !== undefined && (typeof manifest.download_sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(manifest.download_sha256))) {
    throw new Error("Invalid manifest: download_sha256 must be a hexadecimal SHA-256");
  }
  if (manifest.types !== undefined && (typeof manifest.types !== "string" || !manifest.types)) {
    throw new Error("Invalid manifest: types must be a non-empty string");
  }

  const exported = new Set<string>();
  for (const name of manifest.exports.get ?? []) {
    if (exported.has(name)) {
      throw new Error(`Invalid manifest: duplicate export '${name}' in exports.get`);
    }
    exported.add(name);
  }
  return manifest;
}
