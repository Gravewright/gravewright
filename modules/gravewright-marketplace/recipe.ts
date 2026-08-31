import { readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import semver from "semver";
import type { ModuleManifest, ModuleState } from "@gravewright/sdk";
import type { CatalogEntry } from "./catalog.js";
import { resolveDependencyPlanForRoots } from "./dependency-install.js";
import { fetchRemoteJson, prepareInstall, type PreparedInstall, type RevokedRelease } from "./installer.js";

const MAX_RECIPE_BYTES = 512 * 1024;
const MAX_MODULES = 100;
const NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VERSION = /^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$/;

export interface RecipeModule { manifest_url: string; version?: string; state: ModuleState; }
export interface RecipeDocument {
  schema_version: 1;
  kind: "recipe";
  name: string;
  title: string;
  version: string;
  description?: string;
  modules: RecipeModule[];
  capabilities?: Record<string, string>;
}
export interface RecipePlanModule {
  name: string;
  kind: string;
  version: string;
  requested_version: string;
  state: ModuleState;
  manifest_url: string;
  download_sha256: string;
}
export interface RecipePlan { recipe: Pick<RecipeDocument, "name" | "title" | "version">; modules: RecipePlanModule[]; capabilities: Record<string, string>; }

function parseRecipe(value: unknown): RecipeDocument {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("receita deve ser um objeto");
  const object = value as Record<string, unknown>;
  if (object.schema_version !== 1 || object.kind !== "recipe") throw new Error("schema de receita incompatível");
  for (const field of ["name", "title", "version"] as const) if (typeof object[field] !== "string" || !object[field]) throw new Error(`receita sem ${field}`);
  if (!NAME.test(object.name as string) || !VERSION.test(object.version as string)) throw new Error("nome ou versão da receita inválidos");
  if (!Array.isArray(object.modules) || object.modules.length === 0 || object.modules.length > MAX_MODULES) throw new Error("receita deve conter de 1 a 100 módulos");
  const urls = new Set<string>();
  const modules = object.modules.map((item): RecipeModule => {
    if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("módulo inválido na receita");
    const entry = item as Record<string, unknown>;
    if (typeof entry.manifest_url !== "string" || entry.manifest_url.length > 2048) throw new Error("manifest_url inválida na receita");
    if (urls.has(entry.manifest_url)) throw new Error("manifest_url duplicada na receita");
    urls.add(entry.manifest_url);
    if (entry.version !== undefined && typeof entry.version !== "string") throw new Error("restrição de versão inválida");
    if (entry.state !== undefined && entry.state !== "active" && entry.state !== "disabled") throw new Error("estado inválido na receita");
    return { manifest_url: entry.manifest_url, version: (entry.version as string | undefined) ?? "*", state: (entry.state as ModuleState | undefined) ?? "active" };
  });
  let capabilities: Record<string, string> | undefined;
  if (object.capabilities !== undefined) {
    if (!object.capabilities || typeof object.capabilities !== "object" || Array.isArray(object.capabilities)) throw new Error("capabilities inválido na receita");
    capabilities = {};
    for (const [capability, provider] of Object.entries(object.capabilities)) {
      if (!NAME.test(capability.replaceAll(".", "-")) || typeof provider !== "string" || !NAME.test(provider)) throw new Error("capability ou provider inválido na receita");
      capabilities[capability] = provider;
    }
  }
  return {
    schema_version: 1, kind: "recipe", name: object.name as string, title: object.title as string,
    version: object.version as string, ...(typeof object.description === "string" ? { description: object.description } : {}), modules,
    ...(capabilities ? { capabilities } : {}),
  };
}

function tuple(version: string): [number, number, number] | undefined {
  const match = VERSION.exec(version);
  return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : undefined;
}

function accepts(version: string, range: string): boolean {
  if (range === "*" || range === "latest") return Boolean(tuple(version));
  const actual = tuple(version);
  const expected = tuple(range.replace(/^[~^]/, ""));
  if (!actual || !expected) return false;
  if (!range.startsWith("^") && !range.startsWith("~")) return version === range;
  if (range.startsWith("~")) return actual[0] === expected[0] && actual[1] === expected[1] && actual[2] >= expected[2];
  if (expected[0] > 0) return actual[0] === expected[0] && (actual[1] > expected[1] || actual[1] === expected[1] && actual[2] >= expected[2]);
  if (expected[1] > 0) return actual[0] === 0 && actual[1] === expected[1] && actual[2] >= expected[2];
  return actual[0] === 0 && actual[1] === 0 && actual[2] === expected[2];
}

async function readStates(projectRoot: string): Promise<Record<string, ModuleState>> {
  try {
    const value = JSON.parse(await readFile(path.join(projectRoot, "gravewright.modules.json"), "utf8")) as Record<string, unknown>;
    return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, ModuleState] => entry[1] === "active" || entry[1] === "disabled"));
  } catch { return {}; }
}

async function installedManifests(modulesDirectory: string): Promise<ModuleManifest[]> {
  const { readdir } = await import("node:fs/promises");
  const manifests: ModuleManifest[] = [];
  for (const entry of await readdir(modulesDirectory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    try { manifests.push(JSON.parse(await readFile(path.join(modulesDirectory, entry.name, "manifest.json"), "utf8")) as ModuleManifest); } catch { /* ignore */ }
  }
  return manifests;
}

export async function planRecipe(
  recipeUrl: string,
  modulesDirectory: string,
  catalogEntries: readonly CatalogEntry[],
  revoked: readonly RevokedRelease[] = [],
): Promise<RecipePlan> {
  const recipe = parseRecipe(await fetchRemoteJson(recipeUrl, MAX_RECIPE_BYTES));
  const resolved = await resolveDependencyPlanForRoots(recipe.modules.map((item) => item.manifest_url), modulesDirectory, catalogEntries, revoked);
  const explicitByUrl = new Map(recipe.modules.map((item) => [item.manifest_url, item]));
  for (const { manifestUrl, manifest } of resolved) {
    const explicit = explicitByUrl.get(manifestUrl);
    if (explicit && !accepts(manifest.version, explicit.version ?? "*")) throw new Error(`${manifest.name} ${manifest.version} não satisfaz ${explicit.version}`);
  }
  const byName = new Map(resolved.map((item) => [item.manifest.name, item]));
  const explicitByName = new Map(resolved.flatMap((item) => {
    const explicit = explicitByUrl.get(item.manifestUrl);
    return explicit ? [[item.manifest.name, explicit] as const] : [];
  }));
  const active = new Set([...explicitByName].filter(([, item]) => item.state === "active").map(([name]) => name));
  for (const provider of Object.values(recipe.capabilities ?? {})) active.add(provider);
  const pending = [...active];
  while (pending.length) {
    const current = byName.get(pending.pop()!);
    if (!current) continue;
    for (const dependency of Object.keys(current.manifest.dependencies ?? {})) {
      const planned = byName.get(dependency);
      if (!planned || active.has(dependency)) continue;
      if (explicitByName.get(dependency)?.state === "disabled") throw new Error(`${current.manifest.name} ativo requer ${dependency}, mas a receita o desabilita`);
      active.add(dependency); pending.push(dependency);
    }
  }
  const modules = resolved.map(({ manifestUrl, manifest }): RecipePlanModule => {
    const explicit = explicitByUrl.get(manifestUrl);
    return {
      name: manifest.name, kind: manifest.kind, version: manifest.version,
      requested_version: explicit?.version ?? "*",
      state: active.has(manifest.name) ? "active" : explicit?.state ?? "disabled",
      manifest_url: manifestUrl, download_sha256: manifest.download_sha256,
    };
  });
  for (const [capability, providerName] of Object.entries(recipe.capabilities ?? {})) {
    const provider = resolved.find(({ manifest }) => manifest.name === providerName)?.manifest;
    if (!provider) throw new Error(`provider ${providerName} da capability ${capability} não está na receita`);
    if (!provider.provides?.[capability]) throw new Error(`${providerName} não fornece a capability ${capability}`);
    const planned = modules.find((module) => module.name === providerName)!;
    planned.state = "active";
    for (const other of modules) {
      const manifest = resolved.find((item) => item.manifest.name === other.name)!.manifest;
      if (other.name !== providerName && manifest.provides?.[capability]) other.state = "disabled";
    }
  }
  for (const module of modules.filter(({ state }) => state === "active")) {
    const manifest = resolved.find((item) => item.manifest.name === module.name)!.manifest;
    for (const [capability, range] of Object.entries(manifest.requires ?? {})) {
      const providerName = recipe.capabilities?.[capability];
      const provider = providerName ? resolved.find((item) => item.manifest.name === providerName)?.manifest : undefined;
      if (!provider) throw new Error(`${module.name} requer capability ${capability}; escolha um provider em capabilities`);
      if (!provider.provides?.[capability] || !semver.satisfies(provider.provides[capability], range)) throw new Error(`${provider.name} não satisfaz ${capability} ${range}`);
    }
  }
  const states = await readStates(path.dirname(modulesDirectory));
  const installed = await installedManifests(modulesDirectory);
  const currentServers = installed.filter((manifest) => manifest.kind === "server" && states[manifest.name] === "active").length;
  const addedServers = modules.filter((module) => module.kind === "server" && module.state === "active").length;
  if (currentServers + addedServers !== 1) throw new Error("o projeto resultante deve ter exatamente um módulo server ativo");
  return { recipe: { name: recipe.name, title: recipe.title, version: recipe.version }, modules, capabilities: recipe.capabilities ?? {} };
}

async function atomicJson(file: string, value: unknown): Promise<void> {
  const temporary = `${file}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { flag: "wx" });
  await rename(temporary, file);
}

export async function installRecipe(
  recipeUrl: string,
  modulesDirectory: string,
  catalogEntries: readonly CatalogEntry[],
  revoked: readonly RevokedRelease[] = [],
): Promise<RecipePlan> {
  const plan = await planRecipe(recipeUrl, modulesDirectory, catalogEntries, revoked);
  const projectRoot = path.dirname(modulesDirectory);
  const stateFile = path.join(projectRoot, "gravewright.modules.json");
  const lockFile = path.join(projectRoot, "gravewright.lock.json");
  const previousStates = await readStates(projectRoot);
  const previousStateText = await readFile(stateFile, "utf8").catch(() => undefined);
  const previousLockText = await readFile(lockFile, "utf8").catch(() => undefined);
  const prepared: PreparedInstall[] = [];
  try {
    for (const module of plan.modules) {
      const candidate = await prepareInstall(module.manifest_url, modulesDirectory, revoked);
      if (candidate.name !== module.name || candidate.version !== module.version
        || candidate.manifest.download_sha256.toLowerCase() !== module.download_sha256.toLowerCase()) {
        await candidate.cleanup();
        throw new Error(`${module.name}: manifest mudou durante a instalação; tente novamente`);
      }
      prepared.push(candidate);
    }
    for (const module of prepared) await module.commit();
    await atomicJson(stateFile, { ...previousStates, ...Object.fromEntries(plan.modules.map((module) => [module.name, module.state])) });
    await atomicJson(lockFile, { schema_version: 1, recipe: { ...plan.recipe, recipe_url: recipeUrl }, capabilities: plan.capabilities, modules: plan.modules, generated_at: new Date().toISOString() });
    return plan;
  } catch (error) {
    await Promise.allSettled(prepared.map((module) => module.rollback()));
    if (previousStateText !== undefined) await writeFile(stateFile, previousStateText); else await import("node:fs/promises").then(({ rm }) => rm(stateFile, { force: true }));
    if (previousLockText !== undefined) await writeFile(lockFile, previousLockText); else await import("node:fs/promises").then(({ rm }) => rm(lockFile, { force: true }));
    throw error;
  } finally { await Promise.allSettled(prepared.map((module) => module.cleanup())); }
}

export const _recipeTest = { parseRecipe, accepts };
