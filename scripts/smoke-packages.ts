import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execute = promisify(execFile);
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const node = process.execPath;
const root = path.resolve(import.meta.dirname, "..");
const temporary = await mkdtemp(path.join(tmpdir(), "gravewright-package-smoke-"));

try {
  // Pack the exact publishable artifacts rather than importing workspace sources.
  const archives: string[] = [];
  for (const workspace of ["@gravewright/sdk", "@gravewright/kernel"]) {
    const { stdout } = await execute(npm, ["pack", "--json", "--pack-destination", temporary, "-w", workspace], { cwd: root });
    const result = JSON.parse(stdout) as Array<{ filename: string }>;
    if (!result[0]?.filename) throw new Error(`npm pack did not produce ${workspace}`);
    archives.push(path.join(temporary, result[0].filename));
  }
  // Install into an isolated consumer to catch missing files and export-map errors.
  const project = path.join(temporary, "consumer");
  await import("node:fs/promises").then(({ mkdir }) => mkdir(project));
  await writeFile(path.join(project, "package.json"), '{"name":"gravewright-smoke","private":true,"type":"module"}\n');
  await execute(npm, ["install", "--ignore-scripts", "--no-audit", "--no-fund", ...archives], { cwd: project });
  await execute(node, ["--input-type=module", "--eval", `
    import * as sdk from "@gravewright/sdk";
    import { Kernel } from "@gravewright/kernel";
    if (typeof sdk.defineModule !== "function") throw new Error("SDK import failed");
    if (typeof Kernel !== "function") throw new Error("Kernel import failed");
  `], { cwd: project });
  process.stdout.write("Package smoke test passed: @gravewright/sdk and @gravewright/kernel\n");
} finally {
  await rm(temporary, { recursive: true, force: true });
}
