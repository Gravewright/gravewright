#!/usr/bin/env node
import { tsImport } from "tsx/esm/api";

// Load the TypeScript CLI entry without requiring a separately compiled host bundle.
const module = await tsImport("../src/cli/main.ts", import.meta.url);
process.exitCode = await module.main(process.argv.slice(2));
