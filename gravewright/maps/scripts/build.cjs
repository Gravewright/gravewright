// Build the committed framework-independent sources; no original checkout is needed.
const fs = require("fs"),
  path = require("path"),
  { createRequire } = require("module");
const projectRoot = path.resolve(__dirname, "../../..");
const publicStatic = (file, domains) => {
  const parts = path.relative(domains, path.resolve(file)).split(path.sep);
  if (parts.length < 4 || parts[1] !== "static" || parts[2] !== "gravewright_" + parts[0]) return;
  return "/static/" + parts.slice(2).join("/");
};

/** Preserve authored feature boundaries instead of moving them to an anonymous shared chunk. */
async function buildNamedModules({ esbuild, source, output, entries, resources = [], common }) {
  const domains = path.resolve(source, "../..");
  const pixi = { name: "shared-pixi", setup(build) {
    build.onResolve({ filter: /^pixi\.js(?:\/unsafe-eval)?$/ }, () =>
      ({ path: "/static/gravewright_maps/vendor/pixi.js", external: true }));
  } };
  const servedSources = { name: "served-static-source", setup(build) {
    build.onResolve({ filter: /^\./ }, args => {
      if (args.kind === "entry-point") return;
      const url = publicStatic(path.resolve(args.resolveDir, args.path), domains);
      if (url) return { path: url, external: true };
    });
  } };
  const plugins = [...common.plugins, pixi, servedSources];
  // Discover only the modules actually reachable from these public entrypoints.
  // Resources addressed with new URL(..., import.meta.url) are explicit roots.
  const graph = await esbuild.build({ ...common, plugins, entryPoints: [...Object.values(entries), ...resources],
    outdir: output, write: false });
  const modules = Object.keys(graph.metafile.inputs).map(file => path.resolve(file));
  const roots = new Map(Object.entries(entries).map(([name, file]) => [path.resolve(file), path.join(output, name + ".js")]));
  function destination(file) {
    if (roots.has(file)) return roots.get(file);
    const relative = path.relative(source, file);
    if (relative === ".." || relative.startsWith(".." + path.sep) || path.isAbsolute(relative))
      throw Error("A named map module is outside its source tree: " + file);
    return path.join(output, "runtime", relative);
  }
  const boundaries = { name: "named-feature-modules", setup(build) {
    build.onResolve({ filter: /^\./ }, args => {
      if (args.kind === "entry-point") return;
      const target = path.resolve(args.resolveDir, args.path);
      if (publicStatic(target, domains)) return;
      const relative = path.relative(path.dirname(destination(args.importer)), destination(target)).split(path.sep).join("/");
      return { path: relative.startsWith(".") ? relative : "./" + relative, external: true };
    });
  } };
  return esbuild.build({ ...common, plugins: [...plugins, boundaries],
    entryPoints: Object.fromEntries(modules.map(file => [path.relative(output, destination(file)).replace(/\.js$/, "").split(path.sep).join("/"), file])),
    outdir: output });
}

async function buildAssets({ root = projectRoot, outputRoot = root, dependencies = path.join(root, "gravewright/maps/frontend"), manifest = process.env.GRAVEWRIGHT_BUILD_MANIFEST } = {}) {
  const app = path.join(root, "gravewright/maps"), source = path.join(app, "frontend"),
    output = path.join(outputRoot, "gravewright/maps/static/gravewright_maps"),
    otherOutput = (domain, name) => path.join(outputRoot, "gravewright", domain, "static", "gravewright_" + domain, name),
    esbuild = createRequire(path.resolve(dependencies, "package.json"))("esbuild");
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
  const results = [];
  const noticeOutputs = [];
  results.push(await esbuild.build({...common,entryPoints:[source+"/native/table-modules.js"],outfile:otherOutput("table", "media-workspace.js")}));
  results.push(await esbuild.build({...common,entryPoints:[source+"/native/campaign-library.js"],outfile:otherOutput("web", "campaign-manager/library.js")}));
  results.push(await esbuild.build({...common, entryPoints:[source+'/shared/rendering/render-profile.js'], outfile:output+'/render-profile.js'}));
  const worker = source + "/widgets/game-board/model/visibility-worker.js";
  results.push(await buildNamedModules({ esbuild, source, output, common,
    entries: { tools: source + "/native/tools.js", "builder-catalog": source + "/native/builder-catalog.js",
      "builder-editors": source + "/native/builder-editors.js", "builder-native": source + "/native/builder-preview.js",
      "vendor/board": source + "/widgets/game-board/ui/board.js" }, resources: [worker] }));
  results.push(await esbuild.build({ ...common, stdin: { contents: 'import "pixi.js/unsafe-eval"; export * from "pixi.js";',
    resolveDir: source, sourcefile: __filename }, minify: true, outfile: output + "/vendor/pixi.js" }));
  // Keep the previously published worker URL while its real module remains
  // beside visibility-jobs.js for the source's relative new URL() reference.
  results.push(await esbuild.build({ ...common, stdin: {
    contents: 'import "../runtime/widgets/game-board/model/visibility-worker.js";', resolveDir: source, sourcefile: __filename },
    external: [...common.external, "../runtime/*"], outfile: output + "/vendor/visibility-worker.js" }));
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
    [source+'/shared/lib/dom/tree-drag.js',otherOutput('actors', 'tree-drag.js')],
    [source+'/features/tokens/ui/controller.js',otherOutput('tokens', 'controller.js')],
    [app+'/../pdf_system/frontend/controller.js',otherOutput('pdf_system', 'controller.js')]
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
  if (manifest) {
    const outputs = [
      ...results.flatMap(result => Object.keys(result.metafile.outputs).map(name => path.resolve(name))),
      ...noticeOutputs,
      output + "/vendor/packages.json",
    ].map(name => path.relative(outputRoot, name).split(path.sep).join("/"));
    const inputs = results.flatMap(result => Object.keys(result.metafile.inputs))
      .map(name => path.resolve(name))
      .filter(name => !name.split(path.sep).includes("node_modules"))
      .map(name => path.relative(root, name).split(path.sep).join("/"));
    fs.writeFileSync(manifest,
      JSON.stringify({ inputs: [...new Set(inputs)].sort(), outputs: [...new Set(outputs)].sort() }, null, 2) + "\n");
  }
  console.log(
    "Built map assets with " + packages.size + " dependencies; Vue is absent.",
  );
  return results;
}

module.exports = { buildAssets, buildNamedModules };
if (require.main === module) buildAssets({ dependencies: process.argv[2] ? path.resolve(process.argv[2]) : undefined }).catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
