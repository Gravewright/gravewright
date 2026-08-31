import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type GravewrightMarketplaceAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "gravewright-marketplace": GravewrightMarketplaceAPI;
  }
}
