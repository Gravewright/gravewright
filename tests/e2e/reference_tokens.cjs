const fs = require("fs"),
  path = require("path"),
  { createRequire } = require("module");

if (!process.argv[2] || !process.argv[3]) {
  console.error(
    "Usage: node tests/e2e/reference_tokens.cjs <reference-checkout> <output-directory>"
  );
  process.exit(2);
}

const root = path.resolve(process.argv[2]),
  req = createRequire(root + "/package.json"),
  esbuild = req("esbuild"),
  { parse, compileScript } = req("@vue/compiler-sfc");
const css = [];
esbuild
  .build({
    stdin: {
      contents: `import {createApp,h} from 'vue';import TokenEditor from '${root}/src/frontend/src/features/tokens/ui/TokenEditor.vue';import PdfSheet from '${root}/modules/gravewright-pdf-system/frontend/PdfSheet.vue';window.mountReference=(kind,props,host)=>createApp({render:()=>h(kind==='token'?TokenEditor:PdfSheet,props)}).mount(host);`,
      resolveDir: root,
      loader: "ts",
    },
    bundle: true,
    format: "iife",
    target: "es2022",
    nodePaths: [root + "/node_modules"],
    outfile: process.argv[3] + "/reference.js",
    plugins: [
      {
        name: "vue-reference",
        setup(build) {
          build.onLoad({ filter: /\.vue$/ }, (args) => {
            const { descriptor } = parse(fs.readFileSync(args.path, "utf8"), {
              filename: args.path,
            });
            for (const s of descriptor.styles) css.push(s.content);
            return {
              contents: compileScript(descriptor, {
                id: "reference",
                inlineTemplate: true,
              }).content,
              loader: "ts",
              resolveDir: path.dirname(args.path),
            };
          });
        },
      },
    ],
  })
  .then(() => {
    fs.writeFileSync(process.argv[3] + "/reference.css", css.join("\n"));
  })
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
