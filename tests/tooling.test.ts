import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { runtimeTypeSpecifier, syncModuleTypes } from "../scripts/sync-module-types.js";
import { discoverModules } from "../src/discover-modules.js";
import { createModuleStateStore } from "../src/module-state.js";
import { _catalogTest } from "../modules/marketplace/catalog.js";
import { _recipeTest } from "../modules/marketplace/recipe.js";
import { resolveDependencyPlanForRoots } from "../modules/marketplace/dependency-install.js";
import type { CatalogEntry } from "../modules/marketplace/catalog.js";
import type { ModuleManifest } from "@gravewright/sdk";

async function workspace(): Promise<{ modules: string; output: string }> {
  const root = await mkdtemp(path.join(tmpdir(), "gravewright-types-"));
  const modules = path.join(root, "modules");
  const generated = path.join(root, "src", "generated");
  await mkdir(modules, { recursive: true });
  return { modules, output: path.join(generated, "module-types.d.ts") };
}

async function addModule(modules: string, name: string, types?: string): Promise<void> {
  const directory = path.join(modules, name);
  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, "manifest.json"), JSON.stringify({ name, ...(types ? { types } : {}) }));
  if (types?.startsWith("./") && !types.includes("missing")) {
    await writeFile(path.join(directory, types), "export {};\n");
  }
}

test("type sync discovers typed modules, ignores untyped modules and sorts by name", async () => {
  const { modules, output } = await workspace();
  await addModule(modules, "zeta");
  await addModule(modules, "beta", "./types.ts");
  await addModule(modules, "alpha", "./types.ts");
  const first = await syncModuleTypes(modules, output);
  const second = await syncModuleTypes(modules, output);
  assert.equal(first, second);
  assert.equal(await readFile(output, "utf8"), first);
  assert.ok(first.indexOf("alpha/types.js") < first.indexOf("beta/types.js"));
  assert.doesNotMatch(first, /zeta/);
});

test("type sync rejects a missing types file", async () => {
  const { modules, output } = await workspace();
  await addModule(modules, "broken", "./missing.ts");
  await assert.rejects(syncModuleTypes(modules, output), /Module "broken" declares types "\.\/missing\.ts", but the file does not exist/);
});

test("type sync rejects a types path escaping the module", async () => {
  const { modules, output } = await workspace();
  await addModule(modules, "escape", "../outside.ts");
  await assert.rejects(syncModuleTypes(modules, output), /outside its module directory/);
});

test("type sync rejects a types symlink escaping the module", async () => {
  const { modules, output } = await workspace();
  const directory = path.join(modules, "symlink-escape");
  await mkdir(directory);
  const outside = path.join(path.dirname(modules), "outside.ts");
  await writeFile(outside, "export {};\n");
  await writeFile(path.join(directory, "manifest.json"), JSON.stringify({ name: "symlink-escape", types: "./types.ts" }));
  await symlink(outside, path.join(directory, "types.ts"));
  await assert.rejects(syncModuleTypes(modules, output), /outside its module directory/);
});

test("type sync normalizes declaration and module extensions", async () => {
  assert.equal(runtimeTypeSpecifier("types.ts"), "types.js");
  assert.equal(runtimeTypeSpecifier("types.d.ts"), "types.js");
  assert.equal(runtimeTypeSpecifier("types.mts"), "types.mjs");
  assert.equal(runtimeTypeSpecifier("types.d.mts"), "types.mjs");
  assert.equal(runtimeTypeSpecifier("types.cts"), "types.cjs");
  assert.equal(runtimeTypeSpecifier("types.d.cts"), "types.cjs");
  const { modules, output } = await workspace();
  await addModule(modules, "declarations", "./types.d.ts");
  const generated = await syncModuleTypes(modules, output);
  assert.match(generated, /declarations\/types\.js/);
  assert.doesNotMatch(generated, /types\.d\.js/);
});

test("module discovery finds new manifest directories and ignores ordinary directories", async () => {
  const { modules } = await workspace();
  await addModule(modules, "existing-module");
  await mkdir(path.join(modules, "not-a-module"));
  assert.deepEqual((await discoverModules(modules)).map((directory) => path.basename(directory)), ["existing-module"]);
  await addModule(modules, "new-module");
  assert.deepEqual((await discoverModules(modules)).map((directory) => path.basename(directory)), ["existing-module", "new-module"]);
});

test("host delegates startup without concrete module names", async () => {
  const host = await readFile(path.resolve("src/index.ts"), "utf8");
  assert.doesNotMatch(host, /express-server|event-bus|pixi-room|local-campaign|local-marketplace/);
  assert.match(host, /startGravewright/);
});

test("marketplace catalog distinguishes modules and recipes", () => {
  const parsed = _catalogTest.parseCatalog({ schema_version: 1, packages: [
    { type: "module", name: "fog", title: "Fog", version: "1.0.0", manifest_url: "https://example.test/fog.json" },
    { type: "recipe", name: "dark-table", title: "Dark Table", version: "2.0.0", recipe_url: "https://example.test/dark.json" },
  ] }, { name: "Official", url: "https://example.test/catalog.json" });
  assert.deepEqual(parsed.packages.map(({ type, name, catalog }) => ({ type, name, catalog })), [
    { type: "module", name: "fog", catalog: "Official" },
    { type: "recipe", name: "dark-table", catalog: "Official" },
  ]);
});

test("recipes validate shape, defaults and conservative version ranges", () => {
  const recipe = _recipeTest.parseRecipe({
    schema_version: 1, kind: "recipe", name: "dark-table", title: "Dark Table", version: "1.0.0",
    modules: [{ manifest_url: "https://example.test/server.json" }],
  });
  assert.equal(recipe.modules[0]?.state, "active");
  assert.equal(recipe.modules[0]?.version, "*");
  assert.equal(_recipeTest.accepts("1.4.2", "^1.2.0"), true);
  assert.equal(_recipeTest.accepts("2.0.0", "^1.2.0"), false);
  assert.throws(() => _recipeTest.parseRecipe({ ...recipe, modules: [...recipe.modules, ...recipe.modules] }), /duplicada/);
});

test("marketplace resolves transitive dependencies before the requested module", async () => {
  const remote = (name: string, dependencies: Record<string, string> = {}): ModuleManifest & { download_url: string; download_sha256: string } => ({
    name, kind: "addon", provider: "community", version: "1.0.0", entry: "./index.js",
    exports: { get: [] }, dependencies, download_url: `https://example.test/${name}.zip`, download_sha256: "0".repeat(64),
  });
  const manifests = new Map([
    ["root", remote("root", { feature: "^1.0.0" })],
    ["feature", remote("feature", { utility: "^1.0.0" })],
    ["utility", remote("utility")],
  ]);
  const catalog: CatalogEntry[] = ["feature", "utility"].map((name) => ({
    type: "module", name, title: name, version: "1.0.0", manifest_url: name, catalog: "test",
  }));
  const plan = await resolveDependencyPlanForRoots(["root"], "/unused", catalog, [], {
    installed: new Map<string, ModuleManifest>(),
    resolve: async (url) => manifests.get(url)!,
  });
  assert.deepEqual(plan.map(({ manifest }) => manifest.name), ["utility", "feature", "root"]);
});

test("marketplace rejects circular dependency installation", async () => {
  const manifest = (name: string, dependency: string): ModuleManifest & { download_url: string; download_sha256: string } => ({
    name, kind: "addon", provider: "community", version: "1.0.0", entry: "./index.js",
    exports: { get: [] }, dependencies: { [dependency]: "^1.0.0" }, download_url: `https://example.test/${name}.zip`, download_sha256: "0".repeat(64),
  });
  const manifests = new Map([["a", manifest("a", "b")], ["b", manifest("b", "a")]]);
  const catalog: CatalogEntry[] = [{ type: "module", name: "b", title: "b", version: "1.0.0", manifest_url: "b", catalog: "test" }, { type: "module", name: "a", title: "a", version: "1.0.0", manifest_url: "a", catalog: "test" }];
  await assert.rejects(resolveDependencyPlanForRoots(["a"], "/unused", catalog, [], {
    installed: new Map<string, ModuleManifest>(), resolve: async (url) => manifests.get(url)!,
  }), /dependência circular: a -> b -> a/);
});

test("module state store defaults to disabled, persists changes and rejects invalid states", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "gravewright-state-"));
  const statePath = path.join(root, "nested", "gravewright.modules.json");
  const store = await createModuleStateStore(statePath);
  assert.equal(store.get("new-module"), "disabled");
  await store.set("new-module", "active");
  assert.equal(store.get("new-module"), "active");
  assert.deepEqual(JSON.parse(await readFile(statePath, "utf8")), { "new-module": "active" });

  await writeFile(statePath, JSON.stringify({ broken: "banana" }));
  await assert.rejects(createModuleStateStore(statePath), /Invalid module state "banana" for "broken"/);
});

function fakeStateFile(initial = "{}") {
  let final = initial;
  let temporary: string | undefined;
  const calls: string[] = [];
  return {
    calls,
    content: () => final,
    operations: {
      async read() { return final; },
      async mkdir() { calls.push("mkdir"); },
      async write(_file: string, content: string) { calls.push("write"); temporary = content; },
      async rename() { calls.push("rename"); final = temporary!; temporary = undefined; },
      async unlink() { calls.push("unlink"); temporary = undefined; },
    },
  };
}

test("module state store serializes concurrent writes without lost updates", async () => {
  const file = fakeStateFile();
  const store = await createModuleStateStore("/virtual/gravewright.modules.json", file.operations);
  await Promise.all([store.set("foo", "active"), store.set("bar", "active")]);
  assert.equal(file.content(), '{\n  "bar": "active",\n  "foo": "active"\n}\n');
  assert.equal(store.get("bar"), "active");
  assert.equal(store.get("foo"), "active");
});

test("module state store does not commit memory when temp write fails and preserves the main file", async () => {
  const file = fakeStateFile('{"foo":"disabled"}');
  const writeFailure = new Error("temp write failed");
  file.operations.write = async () => { file.calls.push("write"); throw writeFailure; };
  file.operations.unlink = async () => { file.calls.push("unlink"); throw new Error("cleanup failed"); };
  const store = await createModuleStateStore("/virtual/gravewright.modules.json", file.operations);
  await assert.rejects(store.set("foo", "active"), writeFailure);
  assert.equal(store.get("foo"), "disabled");
  assert.equal(file.content(), '{"foo":"disabled"}');
  assert.deepEqual(file.calls, ["mkdir", "write", "unlink"]);
});

test("module state store does not commit memory and cleans temp when rename fails", async () => {
  const file = fakeStateFile('{"foo":"disabled"}');
  const renameFailure = new Error("rename failed");
  file.operations.rename = async () => { file.calls.push("rename"); throw renameFailure; };
  const store = await createModuleStateStore("/virtual/gravewright.modules.json", file.operations);
  await assert.rejects(store.set("foo", "active"), renameFailure);
  assert.equal(store.get("foo"), "disabled");
  assert.equal(file.content(), '{"foo":"disabled"}');
  assert.deepEqual(file.calls, ["mkdir", "write", "rename", "unlink"]);
});
