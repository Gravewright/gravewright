import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { MODULE_KINDS, MODULE_PROVIDERS, ROOM_PROTOCOL, ROOM_SLOT_NAMES, type ModuleKind, type ModuleProvider } from "@gravewright/sdk";

const REQUIRED: Partial<Record<ModuleKind, string[]>> = {
  server: ["start", "stop", "http", "route", "middleware"], room: ["mount", "unmount", "slots"],
  ruleset: [], chat: ["send", "erase"], "dice-engine": ["roll"],
  assets: ["store", "resolve", "mimeTypeAllowed", "remove"], storage: ["create", "find", "where", "update", "delete"],
  backend: [], addon: [],
};

const ROOM_EXPOSES = ROOM_SLOT_NAMES.map((name) => ({ name, mounts: "one" as const, contributions: "many" as const }));

export interface ScaffoldOptions {
  root: string;
  kind: string;
  name: string;
  provider?: string;
  complete?: boolean;
  dryRun?: boolean;
  minimal?: boolean;
  realtime?: boolean;
  tooling?: { read?: boolean; write?: boolean; stat?: boolean };
  author?: string;
  packageName?: string;
  readme?: boolean;
  tests?: boolean;
  initGit?: boolean;
}

export interface ScaffoldResult { directory: string; files: string[]; }

export function normalizeName(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function method(name: string): string {
  if (name === "http") return "      http: {},";
  if (name === "route" || name === "middleware") return `      ${name}() { return () => {}; },`;
  if (name === "slots") return "      slots(_name: string, _module: string, _value: unknown) { return () => {}; },";
  if (name === "read") return "      read(_resource: string) { return undefined; },";
  if (name === "write") return "      write(_resource: string, _value: unknown) {},";
  if (name === "stat") return "      stat(_resource?: string) { return {}; },";
  if (name === "mount") return `      mount(root: HTMLElement) {
        for (const name of ${JSON.stringify(ROOM_SLOT_NAMES)}) {
          const region = root.ownerDocument.createElement("div");
          region.className = name;
          root.append(region);
        }
      },`;
  if (name === "send") return '      send(_message: string) { return crypto.randomUUID(); },';
  if (name === "erase") return "      erase(_messageId: string) {},";
  if (name === "roll") return "      roll(_expression: string) { return 0; },";
  if (name === "store") return '      store(_asset: unknown) { return crypto.randomUUID(); },';
  if (name === "resolve") return "      resolve(_id: string) { return undefined; },";
  if (name === "mimeTypeAllowed") return "      mimeTypeAllowed(_mimeType: string) { return true; },";
  if (name === "remove" || name === "delete") return `      ${name}(_collectionOrId: string, _id?: string) {},`;
  if (name === "create") return "      create(_collection: string, value: unknown) { return value; },";
  if (name === "find") return "      find(_collection: string, _id: string) { return undefined; },";
  if (name === "where") return "      where(_collection: string, _filters: Record<string, unknown>) { return []; },";
  if (name === "update") return "      update(_collection: string, _id: string, value: unknown) { return value; },";
  return `      async ${name}() {},`;
}

export async function scaffoldModule(options: ScaffoldOptions): Promise<ScaffoldResult> {
  if (!MODULE_KINDS.includes(options.kind as ModuleKind)) throw new Error(`Unknown module kind "${options.kind}"`);
  const provider = options.provider ?? "community";
  if (!MODULE_PROVIDERS.includes(provider as ModuleProvider)) throw new Error(`Unknown provider "${provider}"`);
  const name = normalizeName(options.name);
  if (!name) throw new Error("Module name must contain letters or numbers");
  const directory = path.join(options.root, "modules", name);
  if (await access(directory).then(() => true, () => false)) throw new Error(`Module directory already exists: ${directory}`);
  const required = [...(REQUIRED[options.kind as ModuleKind] ?? []), ...(options.kind === "server" && options.realtime ? ["realtime"] : [])];
  const interfaceName = `${name.split("-").map((part) => part[0]?.toUpperCase() + part.slice(1)).join("")}API`;
  const manifest = {
    name, kind: options.kind, provider, version: "0.1.0", entry: "./index.ts", types: "./types.ts",
    ...(options.kind === "room" ? { room_protocol: ROOM_PROTOCOL } : {}),
    ...(options.kind === "room" ? { exposes: { slots: ROOM_EXPOSES } } : {}),
    ...(options.tooling && Object.values(options.tooling).some(Boolean) ? { tooling: Object.fromEntries(Object.entries(options.tooling).filter(([, enabled]) => enabled)) } : {}),
    exports: { get: required },
  };
  const index = [
    'import { defineModule, type Context } from "@gravewright/sdk";', "",
    "export default defineModule({",
    `  name: ${JSON.stringify(name)},`,
    `  kind: ${JSON.stringify(options.kind)},`,
    `  provider: ${JSON.stringify(provider)},`,
    '  version: "0.1.0",',
    ...(options.kind === "room" ? [`  room_protocol: ${JSON.stringify(ROOM_PROTOCOL)},`] : []),
    ...(options.kind === "room" ? [`  exposes: { slots: ${JSON.stringify(ROOM_EXPOSES)} },`] : []),
    ...(options.tooling && Object.values(options.tooling).some(Boolean) ? [`  tooling: ${JSON.stringify(options.tooling)},`] : []),
    `  exports: { get: ${JSON.stringify(required)} },`,
    `  create(${options.complete ? "ctx" : "_ctx"}: Context) {`,
    ...(options.complete ? [
      "    ctx.diagnostic.record({",
      `      event: ${JSON.stringify(`${options.kind}.initialized`)},`,
      '      actor: "System",',
      `      action: ${JSON.stringify(`${options.kind} module initialized`)},`,
      '      status: "success",',
      `      details: { module: ${JSON.stringify(name)} },`,
      "    });",
    ] : []),
    "    return {",
    ...(required.length ? required.map(method) : ["      // declare seus exports aqui"]),
    ...(options.tooling?.read ? ["      read(_topic?: string) { return {}; },"] : []),
    ...(options.tooling?.write ? ["      write(_input?: unknown) { return { ok: true }; },"] : []),
    ...(options.tooling?.stat ? ["      stat() { return { status: \"ready\" }; },"] : []),
    "    };", "  },", "});", "",
  ].join("\n");
  const types = [
    'import type { InferModuleAPI } from "@gravewright/sdk";',
    'import module from "./index.js";', "",
    `export type ${interfaceName} = InferModuleAPI<typeof module>;`, "",
    'declare module "@gravewright/sdk" {',
    "  interface ModuleRegistry {",
    `    ${JSON.stringify(name)}: ${interfaceName};`,
    "  }", "}", "",
  ].join("\n");
  const packageJson = {
    name: options.packageName ?? `@gravewright/${name}`,
    version: "0.1.0",
    private: true,
    type: "module",
    engines: { node: ">=24" },
    peerDependencies: { "@gravewright/sdk": "^0.1.0" },
    ...(options.author ? { author: options.author } : {}),
  };
  const files = new Map<string, string>([
    ["manifest.json", `${JSON.stringify(manifest, null, 2)}\n`],
    ["package.json", `${JSON.stringify(packageJson, null, 2)}\n`],
    ["index.ts", index],
    ["types.ts", types],
  ]);
  if (options.complete || options.readme) {
    files.set("README.md", `# ${name}\n\nComplete ${options.kind} example generated by Gravewright.\n\nThe module starts disabled. Review it, run \`grave doctor\`, then activate it explicitly.\n`);
  }
  if (options.complete || options.tests) {
    files.set("index.test.ts", `import test from "node:test";\nimport assert from "node:assert/strict";\n\ntest(${JSON.stringify(`${name} scaffold`)}, () => {\n  assert.ok(true);\n});\n`);
  }
  if (!options.dryRun) {
    await mkdir(directory, { recursive: true });
    await Promise.all([...files].map(([file, content]) => writeFile(path.join(directory, file), content, { flag: "wx" })));
    if (options.initGit) await promisify(execFile)("git", ["init", "--quiet", directory]);
  }
  return { directory, files: [...files.keys()] };
}
