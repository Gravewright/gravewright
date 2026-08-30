import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MyCampaignAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "my-campaign": MyCampaignAPI;
  }
}
