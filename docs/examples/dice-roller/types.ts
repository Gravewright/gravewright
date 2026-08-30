import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type DiceRollerAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "dice-roller": DiceRollerAPI;
  }
}
