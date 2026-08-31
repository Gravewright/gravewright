# Your first module

This tutorial creates a small `addon` named `hello-table`. It stores one value
and exposes the three commands shared by every module.

## Generate the files

```bash
npm run grave -- new addon hello-table
```

The command creates `modules/hello-table/` with `index.ts`, `manifest.json`,
`package.json`, and `types.ts`. The module starts disabled.

## Implement behavior

Replace the generated factory body with behavior like this:

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "hello-table",
  kind: "addon",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["read", "write", "stat"] },
  create(_ctx) {
    const values = new Map<string, unknown>();
    return {
      read(resource: string) { return values.get(resource); },
      write(resource: string, value: unknown) { values.set(resource, value); },
      stat() { return { entries: values.size }; },
    };
  },
});
```

`read`, `write`, and `stat` are ordinary commands. Their resource vocabulary and
return types belong to your module contract; the POSIX-inspired names do not
imply filesystem access.

## Generate and check static artifacts

```bash
npm run grave -- module build modules/hello-table
npm run grave -- module build modules/hello-table --check
npm run types:sync
npm run typecheck
npm run grave -- doctor
```

The build command derives the manifest and TypeScript registry declaration from
the module definition. `--check` is suitable for CI because it fails on drift.

## Activate deliberately

Set `"hello-table": "active"` in `gravewright.modules.json`, then run `doctor`
again. Installation and scaffolding never activate code automatically.

## Next steps

- Choose the correct [module kind](../concepts/module-kinds.md).
- Learn how [dependencies and capabilities](../concepts/dependencies-and-capabilities.md) differ.
- Read the exact [`defineModule`](../surfaces/define-module.md) contract.
- Copy a [minimal template](../../minimal-templates/README.md).
