import { startGravewright } from "./start-gravewright.js";
import { fileURLToPath } from "node:url";

await startGravewright({ root: fileURLToPath(new URL("..", import.meta.url)) });

console.log("Gravewright initialized");
