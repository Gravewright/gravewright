import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type ServerAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "server": ServerAPI;
  }
}
