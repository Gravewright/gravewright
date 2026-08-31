#!/usr/bin/env node
import { parseArgs } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readFile, readdir } from "node:fs/promises";
import { diagnose } from "./doctor.js";
import { CliOutput } from "./output.js";
import { findProjectRoot } from "./project.js";
import { scaffoldModule } from "./scaffold.js";
import { buildModuleDefinition } from "./module-build.js";
import { DiagnosticJournal, defaultDiagnosticPath } from "../diagnostic-journal.js";
import { startGravewright } from "../start-gravewright.js";

const VERSION = "0.1.0";

const HELP = `Usage: grave <command> [options]

Commands:
  run                      Start the VTT
  new <kind> [name]        Create a module scaffold
  doctor                   Inspect the project
  test [module]            Run declared module self-tests
  module build [path]      Generate manifest and types from defineModule
  help [command]           Show command help

Global options:
  -h, --help               Show help
  -V, --version            Show version
      --no-color           Disable colors

Examples:
  grave run --diagnostic
  grave new addon fog-of-war --example-complete
  grave doctor`;

const COMMAND_HELP: Record<string, string> = {
  run: `Usage: grave run [--diagnostic] [--diagnostic-file <path>]

Starts Gravewright in the current project.
  --diagnostic              Record a safe, readable action journal
  --diagnostic-file <path>  Choose the journal destination`,
  new: `Usage: grave new <kind> [name] [options]

Creates the minimum valid module scaffold.
  --example-complete        Include a documented action example and test
  --minimal                 Generate only the required kind contract
  --read/--write/--stat     Add optional administrative tooling
  --realtime                Add the optional server realtime export
  --provider <provider>     Defaults to community
  --package <name>          Set the npm package name
  --author <name>           Set package author metadata
  --git                     Initialize a Git repository
  --readme                  Generate README.md
  --tests                   Generate a test file
  --dry-run                 Show files without writing them`,
  doctor: `Usage: grave doctor [--json]

Checks project state, manifests, dependencies and required module kinds.`,
  test: `Usage: grave test [module]

Runs optional write tooling for one module or every active module that declares it.`,
  module: `Usage: grave module build [path] [--check]

Generates manifest.json and types.ts from a defineModule() entry.`,
};

export interface MainOptions { cwd?: string; output?: CliOutput; }

function unknown(command: string, output: CliOutput): number {
  const known = ["run", "new", "doctor", "test", "module", "help"];
  const suggestion = known.find((item) => item[0] === command[0]);
  output.error(`grave: unknown command "${command}"`);
  if (suggestion) output.error(`Did you mean "grave ${suggestion}"?`);
  output.error("Try 'grave --help' for usage.");
  return 2;
}

async function toolingModules(root: string, operation: "read" | "write" | "stat"): Promise<string[]> {
  const states = JSON.parse(await readFile(path.join(root, "gravewright.modules.json"), "utf8")) as Record<string, string>;
  const names: string[] = [];
  for (const entry of await readdir(path.join(root, "modules"), { withFileTypes: true })) if (entry.isDirectory()) {
    const manifest = JSON.parse(await readFile(path.join(root, "modules", entry.name, "manifest.json"), "utf8")) as { name: string; tooling?: Record<string, boolean> };
    if (states[manifest.name] === "active" && manifest.tooling?.[operation] === true) names.push(manifest.name);
  }
  return names.sort();
}

async function rootOrFail(cwd: string, output: CliOutput): Promise<string | undefined> {
  const root = await findProjectRoot(cwd);
  if (!root) output.error("grave: no Gravewright project found in this directory or its parents");
  return root;
}

export async function main(argv = process.argv.slice(2), options: MainOptions = {}): Promise<number> {
  const noColor = argv.includes("--no-color");
  argv = argv.filter((arg) => arg !== "--no-color");
  const output = options.output ?? new CliOutput({ color: noColor ? false : undefined });
  const cwd = options.cwd ?? process.cwd();
  if (argv.includes("--version") || argv.includes("-V")) { output.line(`Gravewright ${VERSION}`); return 0; }
  if (!argv.length) {
    output.title(`GRAVEWRIGHT ${VERSION}`);
    output.line("Forge the world. Run the table.\n");
    output.line(HELP);
    return 0;
  }
  const [command, ...rest] = argv;
  if (command === "help" && (!rest[0] || COMMAND_HELP[rest[0]])) { output.line(COMMAND_HELP[rest[0] ?? ""] ?? HELP); return 0; }
  if (command === "--help" || command === "-h") { output.line(HELP); return 0; }
  if (!command || !["run", "new", "doctor", "test", "module", "help"].includes(command)) return unknown(command ?? "", output);
  if (rest.includes("--help") || rest.includes("-h")) { output.line(COMMAND_HELP[command]!); return 0; }

  if (command === "module") {
    const [operation, ...moduleArgs] = rest;
    if (operation !== "build") { output.error("grave module: expected 'build'"); return 2; }
    let parsed;
    try { parsed = parseArgs({ args: moduleArgs, allowPositionals: true, options: { check: { type: "boolean" } } }); }
    catch (error) { output.error(`grave module build: ${error instanceof Error ? error.message : error}`); return 2; }
    const target = path.resolve(cwd, parsed.positionals[0] ?? ".");
    try {
      await buildModuleDefinition(target, { check: parsed.values.check });
      output.pass("Module", parsed.values.check ? "generated files are current" : "manifest and types generated");
      return 0;
    } catch (error) { output.error(`grave module build: ${error instanceof Error ? error.message : error}`); return 1; }
  }

  if (command === "new") {
    let parsed;
    try { parsed = parseArgs({ args: rest, allowPositionals: true, options: { "example-complete": { type: "boolean" }, minimal: { type: "boolean" }, realtime: { type: "boolean" }, read: { type: "boolean" }, write: { type: "boolean" }, stat: { type: "boolean" }, provider: { type: "string" }, package: { type: "string" }, author: { type: "string" }, git: { type: "boolean" }, readme: { type: "boolean" }, tests: { type: "boolean" }, "dry-run": { type: "boolean" } } }); }
    catch (error) { output.error(`grave new: ${error instanceof Error ? error.message : error}`); return 2; }
    const [kind, suppliedName] = parsed.positionals;
    if (!kind) { output.error("grave new: module kind is required"); return 2; }
    let name = suppliedName;
    let wizard: { packageName?: string; author?: string; provider?: string; initGit?: boolean; readme?: boolean; tests?: boolean; read?: boolean; write?: boolean; stat?: boolean } = {};
    if (!name && process.stdin.isTTY) {
      const { createInterface } = await import("node:readline/promises");
      const prompt = createInterface({ input: process.stdin, output: process.stdout });
      name = await prompt.question("Module name: ");
      const yes = async (question: string) => /^(y|yes|s|sim)$/i.test(await prompt.question(`${question} [y/N]: `));
      wizard.packageName = (await prompt.question(`Package name [@gravewright/${name}]: `)) || undefined;
      wizard.author = (await prompt.question("Author: ")) || undefined;
      wizard.provider = (await prompt.question("Provider [community]: ")) || undefined;
      wizard.initGit = await yes("Initialize Git?"); wizard.readme = await yes("Generate README?"); wizard.tests = await yes("Generate tests?");
      wizard.read = await yes("Add read tooling?"); wizard.stat = await yes("Add stat tooling?"); wizard.write = await yes("Add write tooling?");
      prompt.close();
    }
    if (!name) { output.error("grave new: module name is required in non-interactive mode"); return 2; }
    const root = await rootOrFail(cwd, output); if (!root) return 2;
    try {
      const result = await scaffoldModule({ root, kind, name, provider: parsed.values.provider ?? wizard.provider, packageName: parsed.values.package ?? wizard.packageName, author: parsed.values.author ?? wizard.author, initGit: parsed.values.git ?? wizard.initGit, readme: parsed.values.readme ?? wizard.readme, tests: parsed.values.tests ?? wizard.tests, complete: parsed.values["example-complete"], minimal: parsed.values.minimal, realtime: parsed.values.realtime, tooling: { read: parsed.values.read ?? wizard.read, write: parsed.values.write ?? wizard.write, stat: parsed.values.stat ?? wizard.stat }, dryRun: parsed.values["dry-run"] });
      output.title(parsed.values["dry-run"] ? "Module preview" : "Module created");
      output.line();
      output.pass("Kind", kind);
      output.pass("Location", path.relative(root, result.directory));
      output.pass("Template", parsed.values["example-complete"] ? "complete example" : "minimum");
      output.line("\nFiles:");
      for (const file of result.files) output.line(`  ${path.join(path.relative(root, result.directory), file)}`);
      output.line("\nNext: grave doctor");
      return 0;
    } catch (error) { output.error(`grave new: ${error instanceof Error ? error.message : error}`); return 1; }
  }

  if (command === "help" || command === "test") {
    const root = await rootOrFail(cwd, output); if (!root) return 2;
    const operation = command === "help" ? "read" : "write";
    const requested = rest[0];
    const names = requested ? [requested] : await toolingModules(root, operation);
    if (!names.length) { output.warn("Tooling", `No active module declares ${operation}`); return 0; }
    let kernel;
    try {
      kernel = await startGravewright({ root });
      for (const name of names) {
        const result = await kernel.tooling(name, operation, ...(command === "help" && rest[1] ? [rest[1]] : []));
        output.pass(name, typeof result === "string" ? result : JSON.stringify(result, null, 2));
      }
      return 0;
    } catch (error) { output.error(`grave ${command}: ${error instanceof Error ? error.message : error}`); return 1; }
    finally { await kernel?.shutdown(); }
  }

  if (command === "doctor") {
    let parsed;
    try { parsed = parseArgs({ args: rest, options: { json: { type: "boolean" } } }); }
    catch (error) { output.error(`grave doctor: ${error instanceof Error ? error.message : error}`); return 2; }
    const root = await rootOrFail(cwd, output); if (!root) return 2;
    const findings = await diagnose(root);
    if (!findings.some((item) => item.status === "fail")) {
      let kernel;
      try {
        const names = await toolingModules(root, "stat");
        if (names.length) {
          kernel = await startGravewright({ root });
          for (const name of names) findings.push({ status: "pass", label: "Module health", detail: `${name}: ${JSON.stringify(await kernel.tooling(name, "stat"))}` });
        }
      } catch (error) { findings.push({ status: "fail", label: "Module health", detail: error instanceof Error ? error.message : String(error) }); }
      finally { await kernel?.shutdown(); }
    }
    if (parsed.values.json) output.line(JSON.stringify({ ok: !findings.some((item) => item.status === "fail"), findings }, null, 2));
    else {
      output.title("Gravewright Doctor"); output.line();
      for (const finding of findings) output[finding.status](finding.label, finding.detail);
      const failed = findings.filter((item) => item.status === "fail").length;
      const warnings = findings.filter((item) => item.status === "warn").length;
      output.line(`\n${failed} error(s) · ${warnings} warning(s) · ${findings.length - failed - warnings} check(s) passed`);
    }
    return findings.some((item) => item.status === "fail") ? 1 : 0;
  }

  let parsed;
  try { parsed = parseArgs({ args: rest, options: { diagnostic: { type: "boolean" }, "diagnostic-file": { type: "string" } } }); }
  catch (error) { output.error(`grave run: ${error instanceof Error ? error.message : error}`); return 2; }
  const root = await rootOrFail(cwd, output); if (!root) return 2;
  const diagnostic = parsed.values.diagnostic || parsed.values["diagnostic-file"];
  const journal = diagnostic ? await DiagnosticJournal.create(parsed.values["diagnostic-file"] ?? defaultDiagnosticPath(root)) : undefined;
  output.title(`Gravewright ${VERSION}`); output.line();
  output.pass("Project", root);
  if (journal) output.pass("Diagnostic", `Recording safe actions at ${path.relative(root, journal.file)}`);
  try {
    const kernel = await startGravewright({ root, kernel: { diagnostic: journal } });
    journal?.record({ event: "system.start", actor: "System", action: "VTT start", status: "success" });
    output.pass("Runtime", "Table is ready. Press Ctrl+C to stop.");
    let stopping = false;
    const shutdown = async (signal: string) => {
      if (stopping) return;
      stopping = true;
      journal?.record({ event: "system.stop", actor: "System", action: `VTT stop (${signal})`, status: "success" });
      try { await kernel.shutdown(); await journal?.close(); }
      catch (error) { output.fail("Shutdown", error instanceof Error ? error.message : String(error)); process.exitCode = 1; }
    };
    process.once("SIGINT", () => { void shutdown("SIGINT"); });
    process.once("SIGTERM", () => { void shutdown("SIGTERM"); });
    if (journal) {
      const close = () => { void journal.close(); };
      process.once("beforeExit", close);
    }
    return 0;
  } catch (error) {
    journal?.record({ event: "system.start", actor: "System", action: "VTT start", status: "failure", reason: error instanceof Error ? error.message : "Unknown error" });
    await journal?.close();
    output.fail("Runtime", error instanceof Error ? error.message : String(error));
    return 1;
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (invoked === fileURLToPath(import.meta.url)) process.exitCode = await main();
