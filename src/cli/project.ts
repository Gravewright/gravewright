import { access } from "node:fs/promises";
import path from "node:path";

/** Walks upward from a directory until it finds a Gravewright project marker. */
export async function findProjectRoot(start = process.cwd()): Promise<string | undefined> {
  let current = path.resolve(start);
  while (true) {
    try {
      await access(path.join(current, "package.json"));
      const hasState = await access(path.join(current, "gravewright.modules.json")).then(() => true, () => false);
      const hasModules = await access(path.join(current, "modules")).then(() => true, () => false);
      if (hasState || hasModules) return current;
    } catch { /* The current directory is not a project root; keep walking. */ }
    const parent = path.dirname(current);
    if (parent === current) return undefined;
    current = parent;
  }
}
