import fs from "node:fs";
import path from "node:path";

const siteRoot = path.resolve(import.meta.dirname, "../..");
const bundledSnapshotPath = path.join(siteRoot, "wiki", "data", "capabilities.snapshot.json");

function readRegistry(registryPath, source) {
  let document;
  try {
    document = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  } catch (error) {
    throw new Error(`Unable to read the Gravewright capability registry at ${registryPath}: ${error.message}`);
  }

  const registry = document.registry || document;
  if (!registry || typeof registry !== "object" || !registry.capabilities || typeof registry.capabilities !== "object") {
    throw new Error(`Invalid Gravewright capability registry at ${registryPath}: expected an object with a capabilities map.`);
  }
  return { registry, source, path: registryPath, metadata: document.metadata || null };
}

export function resolveCapabilityRegistry() {
  const explicitPath = process.env.GRAVEWRIGHT_CAPABILITIES_PATH;
  if (explicitPath) {
    const resolved = path.resolve(explicitPath);
    if (!fs.existsSync(resolved)) {
      throw new Error(`Gravewright capability registry not found at ${resolved}.\n\nCheck GRAVEWRIGHT_CAPABILITIES_PATH and point it to app/engine/sdk/capabilities.json.`);
    }
    return readRegistry(resolved, "environment");
  }

  if (fs.existsSync(bundledSnapshotPath)) {
    const result = readRegistry(bundledSnapshotPath, "snapshot");
    const commit = result.metadata?.source_commit || "unknown commit";
    console.warn(`WARNING: using bundled capability snapshot from ${commit}`);
    return result;
  }

  throw new Error(
    "Gravewright capability registry not found.\n\n" +
    "Provide:\nGRAVEWRIGHT_CAPABILITIES_PATH=/path/to/gravewright/app/engine/sdk/capabilities.json\n\n" +
    "or generate/update the bundled snapshot.",
  );
}
