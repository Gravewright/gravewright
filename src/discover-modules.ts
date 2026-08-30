import { access, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export async function discoverModules(modulesDirectory: string | URL): Promise<string[]> {
  const root = path.resolve(
    modulesDirectory instanceof URL ? fileURLToPath(modulesDirectory) : modulesDirectory,
  );
  const discovered: string[] = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const moduleDirectory = path.join(root, entry.name);
    try {
      await access(path.join(moduleDirectory, "manifest.json"));
      discovered.push(moduleDirectory);
    } catch {
      // Diretórios sem manifest não são módulos acoplados.
    }
  }
  return discovered.sort((left, right) => left.localeCompare(right));
}
