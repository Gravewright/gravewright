import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import semver from "semver";
import type { ModuleManifest } from "@gravewright/sdk";
import type { CatalogEntry } from "./catalog.js";
import {
  prepareInstall,
  resolveManifest,
  type PreparedInstall,
  type RevokedRelease,
} from "./installer.js";

type RemoteManifest = ModuleManifest & { download_url: string; download_sha256: string };

interface DependencyPlanOptions {
  installed?: ReadonlyMap<string, ModuleManifest>;
  resolve?: (manifestUrl: string, revoked: readonly RevokedRelease[]) => Promise<RemoteManifest>;
}

export interface DependencyInstallResult {
  name: string;
  version: string;
  installed: Array<{ name: string; version: string }>;
}

async function installedModules(modulesDirectory: string): Promise<Map<string, ModuleManifest>> {
  const installed = new Map<string, ModuleManifest>();
  for (const entry of await readdir(modulesDirectory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    try {
      const manifest = JSON.parse(await readFile(path.join(modulesDirectory, entry.name, "manifest.json"), "utf8")) as ModuleManifest;
      if (typeof manifest.name === "string" && typeof manifest.version === "string") installed.set(manifest.name, manifest);
    } catch { /* not an installed module */ }
  }
  return installed;
}

function dependencyEntries(manifest: ModuleManifest): Array<[string, string]> {
  if (manifest.dependencies === undefined) return [];
  if (!manifest.dependencies || typeof manifest.dependencies !== "object" || Array.isArray(manifest.dependencies)) {
    throw new Error(`${manifest.name}: dependencies inválido`);
  }
  return Object.entries(manifest.dependencies).map(([name, range]) => {
    if (!name || typeof range !== "string" || !semver.validRange(range)) throw new Error(`${manifest.name}: dependência ${name} possui range inválido`);
    return [name, range];
  });
}

export async function resolveDependencyPlanForRoots(
  rootManifestUrls: readonly string[],
  modulesDirectory: string,
  catalogEntries: readonly CatalogEntry[],
  revoked: readonly RevokedRelease[] = [],
  options: DependencyPlanOptions = {},
): Promise<Array<{ manifestUrl: string; manifest: RemoteManifest }>> {
  const installed = options.installed ? new Map(options.installed) : await installedModules(modulesDirectory);
  const resolve = options.resolve ?? resolveManifest;
  const sources = new Map(catalogEntries
    .filter((entry): entry is CatalogEntry & { manifest_url: string } => entry.type === "module" && typeof entry.manifest_url === "string")
    .map((entry) => [entry.name, entry.manifest_url]));
  const resolved = new Map<string, { manifestUrl: string; manifest: RemoteManifest }>();
  const visiting: string[] = [];
  const ordered: Array<{ manifestUrl: string; manifest: RemoteManifest }> = [];

  async function visit(manifestUrl: string, expectedName?: string, requiredRange?: string): Promise<RemoteManifest> {
    const manifest = await resolve(manifestUrl, revoked);
    if (expectedName && manifest.name !== expectedName) throw new Error(`catálogo resolveu ${expectedName} como ${manifest.name}`);
    if (requiredRange && !semver.satisfies(manifest.version, requiredRange)) {
      throw new Error(`${manifest.name} ${manifest.version} não satisfaz ${requiredRange}`);
    }
    const previous = resolved.get(manifest.name);
    if (previous) {
      if (requiredRange && !semver.satisfies(previous.manifest.version, requiredRange)) throw new Error(`${manifest.name} não satisfaz todas as dependências`);
      return previous.manifest;
    }
    const cycleAt = visiting.indexOf(manifest.name);
    if (cycleAt !== -1) throw new Error(`dependência circular: ${[...visiting.slice(cycleAt), manifest.name].join(" -> ")}`);
    if (resolved.size >= 100) throw new Error("grafo de dependências excede 100 módulos");
    visiting.push(manifest.name);
    for (const [dependencyName, range] of dependencyEntries(manifest)) {
      const local = installed.get(dependencyName);
      if (local) {
        if (!semver.satisfies(local.version, range)) throw new Error(`${manifest.name} requer ${dependencyName} ${range}, instalado ${local.version}`);
        continue;
      }
      const dependencyUrl = sources.get(dependencyName);
      if (!dependencyUrl) throw new Error(`${manifest.name} requer ${dependencyName} ${range}, mas ele não está instalado nem publicado no catálogo`);
      await visit(dependencyUrl, dependencyName, range);
    }
    visiting.pop();
    const item = { manifestUrl, manifest };
    resolved.set(manifest.name, item);
    ordered.push(item);
    return manifest;
  }

  for (const rootManifestUrl of rootManifestUrls) {
    const root = await visit(rootManifestUrl);
    if (installed.has(root.name)) throw new Error(`módulo ${root.name} já está instalado`);
  }
  return ordered;
}

export async function resolveDependencyPlan(
  rootManifestUrl: string,
  modulesDirectory: string,
  catalogEntries: readonly CatalogEntry[],
  revoked: readonly RevokedRelease[] = [],
): Promise<Array<{ manifestUrl: string; manifest: RemoteManifest }>> {
  return resolveDependencyPlanForRoots([rootManifestUrl], modulesDirectory, catalogEntries, revoked);
}

export async function installWithDependencies(
  rootManifestUrl: string,
  modulesDirectory: string,
  catalogEntries: readonly CatalogEntry[],
  revoked: readonly RevokedRelease[] = [],
): Promise<DependencyInstallResult> {
  const plan = await resolveDependencyPlan(rootManifestUrl, modulesDirectory, catalogEntries, revoked);
  const prepared: PreparedInstall[] = [];
  try {
    for (const item of plan) {
      const candidate = await prepareInstall(item.manifestUrl, modulesDirectory, revoked);
      if (candidate.name !== item.manifest.name
        || candidate.version !== item.manifest.version
        || candidate.manifest.download_sha256.toLowerCase() !== item.manifest.download_sha256.toLowerCase()) {
        await candidate.cleanup();
        throw new Error(`${item.manifest.name}: manifest mudou durante a instalação; tente novamente`);
      }
      prepared.push(candidate);
    }
    for (const item of prepared) await item.commit();
    const root = prepared.at(-1)!;
    return {
      name: root.name,
      version: root.version,
      installed: prepared.map(({ name, version }) => ({ name, version })),
    };
  } catch (error) {
    await Promise.allSettled(prepared.map((item) => item.rollback()));
    throw error;
  } finally {
    await Promise.allSettled(prepared.map((item) => item.cleanup()));
  }
}
