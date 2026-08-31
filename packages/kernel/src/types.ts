import type { Dispose, ModuleManifest, ModuleState } from "@gravewright/sdk";

export interface ModuleRecord {
  manifest: ModuleManifest;
  module: Record<string, unknown>;
  resources: Dispose[];
}

export interface ModuleDefinition {
  manifest: ModuleManifest;
  entryPath: string;
  state: ModuleState;
}

export interface ActivationPlan {
  modules: readonly string[];
  capabilities: Readonly<Record<string, string>>;
  routes: Readonly<Record<string, string>>;
  slots: Readonly<Record<string, readonly string[]>>;
}
