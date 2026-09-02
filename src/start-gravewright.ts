import { Kernel, type KernelOptions } from "@gravewright/kernel";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { discoverModules } from "./discover-modules.js";
import { createModuleStateStore } from "./module-state.js";

/** Configures project discovery and the kernel created by the host. */
export interface StartOptions {
  root?: string;
  kernel?: KernelOptions;
}

/** Discovers installed modules, applies persisted states, and initializes the kernel. */
export async function startGravewright(options: StartOptions = {}): Promise<Kernel> {
  const root = path.resolve(options.root ?? process.cwd());
  const kernel = new Kernel(options.kernel);
  const state = await createModuleStateStore(path.join(root, "gravewright.modules.json"));
  for (const modulePath of await discoverModules(path.join(root, "modules"))) {
    const manifest = JSON.parse(await readFile(path.join(modulePath, "manifest.json"), "utf8")) as { name: string };
    await kernel.load(modulePath, { state: state.get(manifest.name) });
  }
  await kernel.initialize();
  return kernel;
}
