import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MarketplaceAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "marketplace": MarketplaceAPI;
  }
}
