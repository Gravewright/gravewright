import type { Dispose, ModuleManifest, ModuleState } from "@gravewright/sdk";

/** Runtime instance, validated manifest, and resources owned by one active module. */
export interface ModuleRecord {
  manifest: ModuleManifest;
  module: Record<string, unknown>;
  resources: Dispose[];
}

/** Validated module metadata retained before the module is instantiated. */
export interface ModuleDefinition {
  manifest: ModuleManifest;
  entryPath: string;
  state: ModuleState;
}

/** Immutable dependency-safe order in which active modules are instantiated. */
export interface ActivationPlan {
  modules: readonly string[];
}
