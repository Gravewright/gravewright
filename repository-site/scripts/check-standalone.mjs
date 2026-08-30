import { resolve } from "node:path";

const supplied = process.env.GRAVEWRIGHT_CAPABILITIES_PATH;
if (!supplied) {
  throw new Error("Standalone validation requires GRAVEWRIGHT_CAPABILITIES_PATH.");
}

const expected = resolve(supplied);
const { buildCapabilityReference } = await import("../wiki/build/capability-reference.mjs");
const reference = buildCapabilityReference();
if (reference.registrySource !== "environment") {
  throw new Error(`Standalone validation expected the environment registry, got ${reference.registrySource}.`);
}
if (reference.capabilityCount < 1) throw new Error("The supplied registry contains no capabilities.");

console.log(`Standalone registry check passed: ${reference.capabilityCount} capabilities from ${expected}.`);
