import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type GravewrightServerAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "gravewright-server": GravewrightServerAPI;
  }
}
