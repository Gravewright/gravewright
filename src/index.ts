import { startGravewright } from "./start-gravewright.js";
import { fileURLToPath } from "node:url";

// Resolve from this entry file so startup does not depend on the caller's directory.
await startGravewright({ root: fileURLToPath(new URL("..", import.meta.url)) });

console.log("Gravewright initialized");
