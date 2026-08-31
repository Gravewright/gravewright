import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MySystemAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "my-system": MySystemAPI;
  }
}
