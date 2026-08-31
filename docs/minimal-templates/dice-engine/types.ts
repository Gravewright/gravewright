import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MyDiceEngineAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "my-dice-engine": MyDiceEngineAPI;
  }
}
