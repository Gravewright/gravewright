import semver from "semver";
import {
  MODULE_KINDS,
  MODULE_PROVIDERS,
  type ModuleKind,
  type ModuleManifest,
} from "@gravewright/sdk";

/** Narrows a value to a non-null, non-array object. */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Validates an optional array of unique-candidate export names. */
function stringArray(value: unknown, field: string): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item)) {
    throw new Error(`Invalid manifest: ${field} must be an array of non-empty strings`);
  }
  return value as string[];
}

/** Validates and normalizes an untrusted module manifest. */
export function validateManifest(value: unknown): ModuleManifest {
  if (!isObject(value)) throw new Error("Invalid manifest: expected an object");
  const allowedFields = new Set(["name", "kind", "provider", "version", "entry", "types", "dependencies", "tooling", "exports", "manifest_url", "download_url", "download_sha256"]);
  const unknownField = Object.keys(value).find((field) => !allowedFields.has(field));
  if (unknownField) throw new Error(`Invalid manifest: unknown field '${unknownField}'`);
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

  const manifest = {
    name: value.name,
    kind: value.kind,
    provider: value.provider,
    version: value.version,
    entry: value.entry,
    ...(value.types === undefined ? {} : { types: value.types }),
    ...(dependencies === undefined ? {} : { dependencies }),
    ...(value.tooling === undefined ? {} : { tooling: value.tooling }),
    exports: {
      get: stringArray(value.exports.get, "exports.get"),
    },
    ...(value.manifest_url === undefined ? {} : { manifest_url: value.manifest_url }),
    ...(value.download_url === undefined ? {} : { download_url: value.download_url }),
    ...(value.download_sha256 === undefined ? {} : { download_sha256: value.download_sha256 }),
  } as ModuleManifest;

  if (manifest.tooling !== undefined) {
    if (!isObject(manifest.tooling) || Object.entries(manifest.tooling).some(([name, enabled]) => !["read", "write", "stat"].includes(name) || enabled !== true)) {
      throw new Error("Invalid manifest: tooling may only enable read, write, or stat");
    }
  }

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
