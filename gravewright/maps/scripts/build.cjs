// Build the committed framework-independent sources; no original checkout is needed.
const fs = require("fs"),
  path = require("path"),
  { createRequire } = require("module");
const app = path.resolve(__dirname, ".."),
  source = app + "/frontend",
  output = app + "/static/gravewright_maps";
const dependencies = process.argv[2] ? path.resolve(process.argv[2]) : source,
  req = createRequire(dependencies + "/package.json"),
  esbuild = req("esbuild");
const common = {
  bundle: true,
  external: ["/static/*"],
  format: "esm",
  target: "es2022",
  nodePaths: [dependencies + "/node_modules"],
  legalComments: "eof",
  metafile: true,
  plugins: [{ name: 'shared-render-profile', setup(build) {
    build.onResolve({ filter: /render-profile\.js$/ }, args => args.kind === 'entry-point' ? undefined : ({ path: '/static/gravewright_maps/render-profile.js', external: true }));
  } }],
};
(async () => {
  const results = [];
  const noticeOutputs = [];
  results.push(await esbuild.build({...common,entryPoints:[source+"/native/table-modules.js"],outfile:app+"/../table/static/gravewright_table/media-workspace.js"}));
  results.push(await esbuild.build({...common, entryPoints:[source+'/shared/rendering/render-profile.js'], outfile:output+'/render-profile.js'}));
  results.push(await esbuild.build({...common,entryPoints:[source+"/native/tools.js"],outfile:output+"/tools.js"}));
  results.push(
    await esbuild.build({
      ...common,
      entryPoints: [source + "/widgets/game-board/ui/board.js"],
      splitting: true,
      minify: true,
      outdir: output + "/vendor",
    }),
  );
  results.push(
    await esbuild.build({
      ...common,
      entryPoints: [
        source + "/features/walls/ui/walls.js",
        source + "/features/walls/model/walls.js",
      ],
      outbase: source + "/features/walls",
      outdir: output + "/walls",
    }),
  );
  results.push(
    await esbuild.build({
      ...common,
      entryPoints: [
        source + "/features/scene-layers/ui/sources.js",
        source + "/features/lighting/model/light-profiles.js",
      ],
      entryNames: "[name]",
      outdir: output + "/sources",
    }),
  );
  results.push(
    await esbuild.build({
      ...common,
      entryPoints: [source + "/calibration.js"],
      outfile: output + "/calibration-model.js",
    }),
  );
  results.push(
    await esbuild.build({
      ...common,
      entryPoints: [source + "/directory.js"],
      outfile: output + "/directory.js",
    }),
  );
  for(const [entry,outfile] of [
    [source+'/shared/lib/dom/tree-drag.js',app+'/../actors/static/gravewright_actors/tree-drag.js'],
    [source+'/features/tokens/ui/controller.js',app+'/../tokens/static/gravewright_tokens/controller.js'],
    [app+'/../pdf_system/frontend/controller.js',app+'/../pdf_system/static/gravewright_pdf_system/controller.js']
  ]) results.push(await esbuild.build({...common,entryPoints:[entry],outfile}));
  const packages = new Map(),
    licenses = output + "/vendor/licenses";
  fs.mkdirSync(licenses, { recursive: true });
  for (const result of results)
    for (const input of Object.keys(result.metafile.inputs)) {
      if (!input.includes("node_modules")) continue;
      let dir = path.dirname(path.resolve(input));
      while (!fs.existsSync(dir + "/package.json") && dir !== path.dirname(dir))
        dir = path.dirname(dir);
      const pkg = JSON.parse(fs.readFileSync(dir + "/package.json", "utf8"));
      if (pkg.name === "vue" || pkg.name?.startsWith("@vue/"))
        throw Error("Vue cannot be included in map assets");
      packages.set(pkg.name, {
        name: pkg.name,
        version: pkg.version,
        license: pkg.license,
      });
      for (const name of fs
        .readdirSync(dir)
        .filter((n) => /^(license|licence|notice)(\.|$)/i.test(n)))
        if (fs.statSync(dir + "/" + name).isFile()) {
          const destination = licenses + "/" + pkg.name.replaceAll("/", "_") + "-" + name;
          fs.copyFileSync(
            dir + "/" + name,
            destination,
          );
          noticeOutputs.push(destination);
        }
    }
  fs.writeFileSync(
    output + "/vendor/packages.json",
    JSON.stringify([...packages.values()], null, 2) + "\n",
  );
  // Runner caching must include every generated chunk and legal notice. Other
  // builds keep the normal output and do not need a private Runner manifest.
  if (process.env.GRAVEWRIGHT_BUILD_MANIFEST) {
    const root = path.resolve(app, "../..");
    const outputs = [
      ...results.flatMap(result => Object.keys(result.metafile.outputs).map(name => path.resolve(name))),
      ...noticeOutputs,
      output + "/vendor/packages.json",
    ].map(name => path.relative(root, name).split(path.sep).join("/"));
    const inputs = results.flatMap(result => Object.keys(result.metafile.inputs))
      .map(name => path.resolve(name))
      .filter(name => !name.split(path.sep).includes("node_modules"))
      .map(name => path.relative(root, name).split(path.sep).join("/"));
    fs.writeFileSync(process.env.GRAVEWRIGHT_BUILD_MANIFEST,
      JSON.stringify({ inputs: [...new Set(inputs)].sort(), outputs: [...new Set(outputs)].sort() }, null, 2) + "\n");
  }
  console.log(
    "Built map assets with " + packages.size + " dependencies; Vue is absent.",
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
