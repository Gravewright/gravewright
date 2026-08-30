import { access, mkdir, readFile, realpath, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { discoverModules } from "../src/discover-modules.js";

interface TypeEntry {
  name: string;
  typePath: string;
}

export function runtimeTypeSpecifier(filePath: string): string {
  return filePath
    .replace(/\.d\.mts$/, ".mjs")
    .replace(/\.d\.cts$/, ".cjs")
    .replace(/\.d\.ts$/, ".js")
    .replace(/\.mts$/, ".mjs")
    .replace(/\.cts$/, ".cjs")
    .replace(/\.tsx?$/, ".js");
}

export async function syncModuleTypes(
  modulesDirectory: string,
  outputPath: string,
): Promise<string> {
  const modulesRoot = path.resolve(modulesDirectory);
  const entries: TypeEntry[] = [];

  for (const moduleDirectory of await discoverModules(modulesRoot)) {
    const manifestPath = path.join(moduleDirectory, "manifest.json");
    let manifest: unknown;
    try {
      manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    } catch (error) {
      throw new Error(`Cannot read manifest ${manifestPath}`, { cause: error });
    }
    if (typeof manifest !== "object" || manifest === null) {
      throw new Error(`Invalid manifest: ${manifestPath}`);
    }
    const { name, types } = manifest as { name?: unknown; types?: unknown };
    if (types === undefined) continue;
    if (typeof name !== "string" || !name || typeof types !== "string" || !types) {
      throw new Error(`Invalid name or types in ${manifestPath}`);
    }
    const requestedTypePath = path.resolve(moduleDirectory, types);
    const relativeToModule = path.relative(moduleDirectory, requestedTypePath);
    if (relativeToModule.startsWith("..") || path.isAbsolute(relativeToModule)) {
      throw new Error(`Module "${name}" declares types "${types}" outside its module directory`);
    }
    let typePath: string;
    try {
      await access(requestedTypePath);
      typePath = await realpath(requestedTypePath);
    } catch {
      throw new Error(`Module "${name}" declares types "${types}", but the file does not exist`);
    }
    const relativeRealType = path.relative(await realpath(moduleDirectory), typePath);
    if (relativeRealType.startsWith("..") || path.isAbsolute(relativeRealType)) {
      throw new Error(`Module "${name}" declares types "${types}" outside its module directory`);
    }
    entries.push({ name, typePath });
  }

  entries.sort((left, right) => left.name.localeCompare(right.name));
  const outputDirectory = path.dirname(path.resolve(outputPath));
  const imports = entries.map(({ typePath }) => {
    let relative = path.relative(outputDirectory, typePath).replaceAll(path.sep, "/");
    if (!relative.startsWith(".")) relative = `./${relative}`;
    relative = runtimeTypeSpecifier(relative);
    return `import ${JSON.stringify(relative)};`;
  });
  const content = ["// AUTO-GENERATED.", "// DO NOT EDIT.", "", ...imports, ""].join("\n");
  await mkdir(outputDirectory, { recursive: true });
  await writeFile(outputPath, content);
  return content;
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  await syncModuleTypes(path.join(root, "modules"), path.join(root, "src/generated/module-types.d.ts"));
}
