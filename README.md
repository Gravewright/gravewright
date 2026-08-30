# Gravewright

**Build a virtual tabletop from modules, not assumptions.**

Gravewright is an open-source platform for creating Virtual Tabletops from independent, replaceable modules. It provides a small TypeScript microkernel and lets each distribution decide how campaigns, rooms, rules, rendering, assets, UI, and discovery should work.

[Português (Brasil)](README.pt-BR.md) · [Documentation](docs/README.md) · [Create a module](docs/en/creating-a-module.md)

## One kernel, many VTTs

```text
                         ┌─────────────────────┐
                         │ Gravewright Kernel  │
                         │ validate · compose  │
                         │     lifecycle       │
                         └──────────┬──────────┘
                                    │
                            one active server
                                    │
          ┌─────────────┬───────────┼───────────┬─────────────┐
          │             │           │           │             │
      Campaign         Room       Ruleset   Marketplace       UI
                        │                       │
                    Renderer               Modules &
                        │                   Recipes
                      Assets
```

Use the official modules, replace one part of the stack, or ship a completely different experience. The kernel coordinates the system without owning its product decisions.

## What Gravewright provides

- A deliberately small microkernel for validation, composition, and lifecycle.
- Static manifests that can be inspected before module code executes.
- Typed module APIs through `@gravewright/sdk` and `ctx.use()`.
- Routes, middleware, and slots without coupling modules to a web framework.
- Scaffolding, diagnostics, health checks, and manifest tooling through `grave`.
- A release-based marketplace with verified archives and reproducible recipes.

The only structural requirement is exactly one active `server` module. Gravewright defines its minimum contract, not its implementation: Express, Fastify, or another transport can satisfy it.

## Quick start

```bash
npm install
cp gravewright.modules.example.json gravewright.modules.json
npm test
npm run typecheck
npm run grave -- doctor
npm run grave -- run
```

The default marketplace is available at `http://127.0.0.1:3000/marketplace`.

## Create a module

```bash
npm run grave -- new addon fog-of-war
npm run grave -- module build modules/fog-of-war
npm run grave -- doctor
```

Start with the [module authoring guide](docs/en/creating-a-module.md), copy a [minimal template](docs/minimal-templates/), or study the [complete examples](docs/examples/).

## Principles

- **Small kernel:** mechanisms belong in the core; product policy does not.
- **Replaceable implementations:** no renderer, rules engine, or storage model is universal.
- **Explicit contracts:** dependencies and public capabilities are declared and validated.
- **Composition over coupling:** a VTT is a compatible set of modules.
- **Independent evolution:** modules can be maintained and released separately.
- **Distribution freedom:** Gravewright is a foundation, not a prescribed VTT.

## Workspace

```text
gravewright/
├── bin/                 `grave` executable
├── docs/                author documentation, templates, and examples
├── modules/             installed modules
│   ├── server/          minimal server implementation
│   └── marketplace/     catalogs, installation, and recipes
├── packages/
│   ├── kernel/          microkernel runtime (Apache-2.0)
│   └── sdk/             public author contracts (MIT)
├── scripts/             development tooling
├── src/                 host and CLI
└── tests/               kernel, CLI, and tooling tests
```

## License

`@gravewright/sdk` is licensed under MIT. `@gravewright/kernel` is licensed under Apache-2.0. Third-party modules remain under their respective licenses.
