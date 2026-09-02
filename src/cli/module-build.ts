import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import type { DefinedModule, ModuleManifest } from "@gravewright/sdk";

/** Converts a kebab-case module identifier into its generated API type name. */
function pascal(value: string): string {
  return `${value.split("-").map((part) => part[0]?.toUpperCase() + part.slice(1)).join("")}API`;
}

/** Chooses whether generated module files are written or only verified. */
export interface BuildModuleOptions { check?: boolean; }

/** Generates a manifest and registry augmentation from a `defineModule` entry. */
export async function buildModuleDefinition(directory: string, options: BuildModuleOptions = {}): Promise<void> {
  const root = path.resolve(directory);
  const entryPath = path.join(root, "index.ts");
  const imported = await import(`${pathToFileURL(entryPath).href}?build=${Date.now()}`) as { default?: DefinedModule };
  const module = imported.default;
  if (typeof module !== "function" || !module.definition) throw new Error("default export must be created with defineModule()");
  const definition = module.definition;
  const manifest: ModuleManifest = {
    name: definition.name,
    kind: definition.kind,
    provider: definition.provider,
    version: definition.version,
    entry: "./index.ts",
    types: "./types.ts",
    ...(definition.manifest_url ? { manifest_url: definition.manifest_url } : {}),
    ...(definition.download_url ? { download_url: definition.download_url } : {}),
    ...(definition.download_sha256 ? { download_sha256: definition.download_sha256 } : {}),
    ...(definition.dependencies ? { dependencies: definition.dependencies } : {}),
    ...(definition.tooling ? { tooling: definition.tooling } : {}),
    exports: {
      get: [...(definition.exports.get ?? [])],
    },
  };
  const interfaceName = pascal(definition.name);
  const types = [
    'import type { InferModuleAPI } from "@gravewright/sdk";',
    'import module from "./index.js";', "",
    `export type ${interfaceName} = InferModuleAPI<typeof module>;`, "",
    'declare module "@gravewright/sdk" {', "  interface ModuleRegistry {",
    `    ${JSON.stringify(definition.name)}: ${interfaceName};`, "  }", "}", "",
  ].join("\n");
  const outputs = new Map([[path.join(root, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`], [path.join(root, "types.ts"), types]]);
  for (const [file, expected] of outputs) {
    if (options.check) {
      const actual = await readFile(file, "utf8").catch(() => "");
      if (actual !== expected) throw new Error(`${path.basename(file)} is stale; run grave module build`);
    } else await writeFile(file, expected);
  }
}
