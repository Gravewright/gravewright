// Run the original algorithm assertions against the transposed local sources.
const fs = require("fs"),
  path = require("path"),
  os = require("os"),
  { createRequire } = require("module"),
  { spawnSync } = require("child_process");
const source = path.resolve(__dirname, '../frontend');
const dependencies = process.argv[2] ? path.resolve(process.argv[2]) : source;
const req = createRequire(dependencies + '/package.json');
const tests = [];
for (const dir of ['widgets/game-board/model', 'features/walls/model', 'features/tokens/model', 'features/drawing/model', 'features/measurement/model', 'features/effects/model', 'features/selection/model'])
  for (const name of fs.readdirSync(source + '/' + dir).filter(n => n.endsWith('.test.js')))
    tests.push(source + '/' + dir + '/' + name);
tests.push(path.resolve(source,'../../pdf_system/frontend/mapping.test.js'));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "grave-map-models-"));
try {
  req("esbuild").buildSync({
    entryPoints: tests,
    bundle: true,
    platform: "node",
    format: "esm",
    outdir: temp,
    entryNames: "[name]",
    outExtension: { ".js": ".mjs" },
  });
  const r = spawnSync(
    process.execPath,
    [
      "--test",
      ...fs
        .readdirSync(temp)
        .filter((f) => f.endsWith(".mjs"))
        .map((f) => temp + "/" + f),
    ],
    { stdio: "inherit" },
  );
  process.exitCode = r.status ?? 1;
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
