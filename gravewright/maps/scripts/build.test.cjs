const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const { pathToFileURL } = require("node:url");
const { test } = require("node:test");
const { buildAssets, buildNamedModules } = require("./build.cjs");

const root = path.resolve(__dirname, "../../..");
const temporaryRoot = path.join(root, "data/runner");
const esbuild = createRequire(path.join(root, "gravewright/maps/frontend/package.json"))("esbuild");

function temporary(test) {
  fs.mkdirSync(temporaryRoot, { recursive: true });
  const directory = fs.mkdtempSync(path.join(temporaryRoot, "map-build-tests-"));
  test.after(() => {
    const resolved = fs.realpathSync(directory);
    assert.ok(resolved.startsWith(fs.realpathSync(temporaryRoot) + path.sep));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  return directory;
}

function write(file, contents) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, contents);
}

test("named modules retain identity, lazy imports and worker URLs inside an installation named static", async test => {
  const directory = temporary(test), source = path.join(directory, "static", "installation", "frontend"), output = path.join(directory, "output");
  write(path.join(directory, "package.json"), '{"type":"module"}');
  write(path.join(source, "native/tools.js"), `
    import { identity } from '../features/selection/model/objects.js';
    export { identity };
    export const preview = () => import('./preview.js');
  `);
  write(path.join(source, "native/preview.js"), `
    import { identity } from '../features/selection/model/objects.js';
    import { workerUrl } from '../widgets/game-board/model/visibility-jobs.js';
    export { identity, workerUrl };
  `);
  write(path.join(source, "features/selection/model/objects.js"), "export const identity = {};");
  write(path.join(source, "widgets/game-board/model/visibility-jobs.js"),
    "export const workerUrl = new URL('./visibility-worker.js', import.meta.url);");
  const worker = path.join(source, "widgets/game-board/model/visibility-worker.js");
  write(worker, `
    import { identity } from '../../../features/selection/model/objects.js';
    export { identity };
  `);
  const result = await buildNamedModules({ esbuild, source, output,
    entries: { tools: path.join(source, "native/tools.js"), "builder-native": path.join(source, "native/preview.js") },
    resources: [worker], common: { bundle: true, format: "esm", target: "es2022", metafile: true, plugins: [] } });
  const files = Object.keys(result.metafile.outputs).map(file => path.relative(output, path.resolve(file)));
  assert.equal(files.length, 5);
  assert.ok(files.every(file => !file.includes("chunk-") && !file.includes("node_modules")));
  const tools = await import(pathToFileURL(path.join(output, "tools.js")));
  const preview = await tools.preview();
  assert.equal(tools.identity, preview.identity);
  assert.ok(fs.existsSync(preview.workerUrl));
  assert.equal((await import(preview.workerUrl)).identity, tools.identity);
  assert.match(fs.readFileSync(path.join(output, "tools.js"), "utf8"), /import\("\.\/builder-native\.js"\)/);
});

test("the complete build reports every named module, public entry and license to Runner", async test => {
  const outputRoot = temporary(test), manifest = path.join(outputRoot, "build-outputs.json");
  const results = await buildAssets({ outputRoot, manifest });
  const built = JSON.parse(fs.readFileSync(manifest, "utf8"));
  for (const name of built.outputs) {
    const file = path.resolve(outputRoot, name);
    assert.ok(file.startsWith(outputRoot + path.sep));
    assert.ok(fs.statSync(file).isFile(), name);
  }
  assert.ok(built.inputs.every(name => fs.statSync(path.join(root, name)).isFile()));
  const maps = "gravewright/maps/static/gravewright_maps/";
  for (const name of ["tools.js", "builder-native.js", "builder-editors.js", "builder-catalog.js", "render-profile.js",
    "vendor/board.js", "vendor/visibility-worker.js", "vendor/pixi.js", "vendor/packages.json",
    "runtime/widgets/game-board/model/visibility-worker.js"])
    assert.ok(built.outputs.includes(maps + name), name);
  assert.ok(built.outputs.some(name => name.startsWith(maps + "vendor/licenses/")));
  const inputs = results.flatMap(result => Object.keys(result.metafile.inputs));
  assert.ok(inputs.some(name => name.includes("pixi.js/") && name.includes("unsafe-eval")));
  const tools = fs.readFileSync(path.join(outputRoot, maps, "tools.js"), "utf8");
  assert.ok(tools.includes("runtime/features/selection/ui/selection-workspace.js"));
  assert.ok(!tools.includes("function createSelection("));
  const preview = fs.readFileSync(path.join(outputRoot, maps, "builder-native.js"), "utf8");
  assert.ok(preview.includes("/static/gravewright_maps/vendor/pixi.js"));
  assert.ok(preview.includes("/static/gravewright_maps/render-profile.js"));
  assert.ok(!built.outputs.some(name => /chunk-.*\.js$/.test(name)));
});
