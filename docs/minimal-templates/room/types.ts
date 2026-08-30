import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type MyRoomAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "my-room": MyRoomAPI;
  }
}
