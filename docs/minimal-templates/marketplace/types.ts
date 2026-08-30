import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MyMarketplaceAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "my-marketplace": MyMarketplaceAPI;
  }
}
