import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fetchRemoteJson, type RevokedRelease } from "./installer.js";

const MAX_CATALOG_BYTES = 2 * 1024 * 1024;
const OFFICIAL_CATALOG: CatalogConfig = {
  name: "Gravewright Official",
  url: "https://raw.githubusercontent.com/Gravewright/marketplace/main/gravewright.marketplace.json",
};

export interface CatalogEntry {
  type: "module" | "recipe";
  name: string;
  title: string;
  description?: string;
  version: string;
  kind?: string;
  provider?: string;
  tags?: string[];
  manifest_url?: string;
  recipe_url?: string;
  catalog: string;
}

export interface CatalogResult {
  packages: CatalogEntry[];
  revoked: RevokedRelease[];
  warnings: string[];
}

interface CatalogConfig { name: string; url: string; }

function parseCatalog(value: unknown, source: CatalogConfig): Omit<CatalogResult, "warnings"> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("catálogo deve ser um objeto");
  const object = value as Record<string, unknown>;
  if (object.schema_version !== 1 || !Array.isArray(object.packages)) throw new Error("schema de catálogo incompatível");
  const packages = object.packages.map((item): CatalogEntry => {
    if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("entrada de catálogo inválida");
    const entry = item as Record<string, unknown>;
    if (entry.type !== "module" && entry.type !== "recipe") throw new Error("tipo de entrada inválido");
    for (const field of ["name", "title", "version"] as const) if (typeof entry[field] !== "string" || !entry[field]) throw new Error(`entrada sem ${field}`);
    const target = entry.type === "module" ? entry.manifest_url : entry.recipe_url;
    if (typeof target !== "string" || !target) throw new Error(`entrada sem ${entry.type === "module" ? "manifest_url" : "recipe_url"}`);
    return {
      type: entry.type,
      name: entry.name as string,
      title: entry.title as string,
      version: entry.version as string,
      ...(typeof entry.description === "string" ? { description: entry.description } : {}),
      ...(typeof entry.kind === "string" ? { kind: entry.kind } : {}),
      ...(typeof entry.provider === "string" ? { provider: entry.provider } : {}),
      ...(Array.isArray(entry.tags) && entry.tags.every((tag) => typeof tag === "string") ? { tags: entry.tags as string[] } : {}),
      ...(entry.type === "module" ? { manifest_url: target as string } : { recipe_url: target as string }),
      catalog: source.name,
    };
  });
  const revoked = Array.isArray(object.revoked) ? object.revoked.filter((item): item is RevokedRelease => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return false;
    const entry = item as Record<string, unknown>;
    return typeof entry.name === "string"
      && (entry.version === undefined || typeof entry.version === "string")
      && (entry.download_sha256 === undefined || typeof entry.download_sha256 === "string");
  }) : [];
  return { packages, revoked };
}

async function configuredCatalogs(projectRoot: string): Promise<CatalogConfig[]> {
  const fromEnvironment = process.env.GRAVEWRIGHT_CATALOGS?.split(",").map((url, index) => ({ name: `Catalog ${index + 1}`, url: url.trim() })).filter((entry) => entry.url) ?? [];
  try {
    const parsed = JSON.parse(await readFile(path.join(projectRoot, "gravewright.marketplace.local.json"), "utf8")) as { catalogs?: unknown };
    if (!Array.isArray(parsed.catalogs)) return [OFFICIAL_CATALOG, ...fromEnvironment];
    const fromFile = parsed.catalogs.filter((entry): entry is CatalogConfig => Boolean(entry) && typeof entry === "object"
      && typeof (entry as CatalogConfig).name === "string" && typeof (entry as CatalogConfig).url === "string");
    return [OFFICIAL_CATALOG, ...fromFile, ...fromEnvironment];
  } catch { return [OFFICIAL_CATALOG, ...fromEnvironment]; }
}

export async function loadCatalogs(projectRoot: string): Promise<CatalogResult> {
  const configs = await configuredCatalogs(projectRoot);
  const result: CatalogResult = { packages: [], revoked: [], warnings: [] };
  const cacheDirectory = path.join(projectRoot, ".gravewright", "cache", "marketplace");
  await mkdir(cacheDirectory, { recursive: true });
  for (const config of configs) {
    const cache = path.join(cacheDirectory, `${createHash("sha256").update(config.url).digest("hex")}.json`);
    let document: unknown;
    try {
      document = await fetchRemoteJson(config.url, MAX_CATALOG_BYTES);
      const parsed = parseCatalog(document, config);
      await writeFile(cache, `${JSON.stringify(document)}\n`);
      result.packages.push(...parsed.packages); result.revoked.push(...parsed.revoked);
      continue;
    } catch (remoteError) {
      try {
        document = JSON.parse(await readFile(cache, "utf8"));
        const parsed = parseCatalog(document, config);
        result.packages.push(...parsed.packages); result.revoked.push(...parsed.revoked);
        result.warnings.push(`${config.name}: usando cache local`);
      } catch {
        result.warnings.push(`${config.name}: indisponível`);
      }
    }
  }
  const unique = new Map(result.packages.map((entry) => [`${entry.type}:${entry.name}`, entry]));
  result.packages = [...unique.values()].sort((left, right) => left.title.localeCompare(right.title));
  return result;
}

export const _catalogTest = { parseCatalog };
