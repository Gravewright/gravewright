# Gravewright

**Build a virtual tabletop from modules, not assumptions.**

Gravewright is an open-source platform for creating Virtual Tabletops from independent, replaceable modules. It provides a small TypeScript microkernel and lets each distribution decide how its table, rules, backend, extensions, and transport should work.

[Português (Brasil)](README.pt-BR.md) · [Documentation](docs/README.md) · [Create a module](docs/en/creating-a-module.md) · [Release readiness](docs/en/reference/release-readiness.md)

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
                ┌───────────┬───────┴───────┬───────────┐
                │           │               │           │
              Room       Ruleset          Addon       Backend
         campaign/table  game rules    extensions    backend
```

Use the official modules, replace one part of the stack, or ship a completely different experience. The kernel coordinates the backend without owning its product decisions.

## What Gravewright provides

- A deliberately small microkernel for validation, composition, and lifecycle.
- Static manifests that can be inspected before module code executes.
- Typed concrete, structural, and semantic resolution through `ctx.use()`, `ctx.kind()`, and `ctx.capability()`.
- Routes, middleware, and slots without coupling modules to a web framework.
- Scaffolding, diagnostics, health checks, and manifest tooling through `grave`.
- A release-based marketplace with verified archives and reproducible recipes.

Every running project has exactly one active `server`. `room`, `ruleset`, `chat`,
`dice-engine`, `assets`, and `storage` are optional singletons; `backend` and
`addon` are plural. Recipes may require a room or ruleset without turning that
product policy into a kernel invariant.

## Quick start

```bash
npm install
npm test
npm run typecheck
npm run grave -- doctor
npm run grave -- run
```

The tracked `gravewright.modules.json` is this repository's default composition.
Marketplace installation never changes activation state automatically.

The default marketplace is available at `http://127.0.0.1:3000/marketplace`.

## Create a module

```bash
npm run grave -- new addon fog-of-war
npm run grave -- module build modules/fog-of-war
npm run grave -- doctor
```

Start with the [documentation path for new authors](docs/en/getting-started/README.md), use the [complete module guide](docs/en/creating-a-module.md), copy a [minimal template](docs/minimal-templates/), or study the [complete examples](docs/examples/).

## Principles

- **Small kernel:** mechanisms belong in the core; product policy does not.
- **Replaceable implementations:** no renderer, rules engine, or storage model is universal.
- **Explicit contracts:** dependencies and public capabilities are declared and validated.
- **Transactional lifecycle:** activation is planned first; resources roll back and shut down in reverse order.
- **Replaceable capabilities:** consumers require versioned contracts while recipes choose providers.
- **Composition over coupling:** a VTT is a compatible set of modules.
- **Independent evolution:** modules can be maintained and released separately.
- **Distribution freedom:** Gravewright is a foundation, not a prescribed VTT.

## Workspace

```text
gravewright/
├── bin/                 `grave` executable
├── docs/                author documentation, templates, and examples
├── modules/             installed modules
│   ├── gravewright-server/       minimal server implementation
│   └── gravewright-marketplace/  catalogs, installation, and recipes
├── packages/
│   ├── kernel/          microkernel runtime (Apache-2.0)
│   └── sdk/             public author contracts (MIT)
├── scripts/             development tooling
├── src/                 host and CLI
└── tests/               kernel, CLI, and tooling tests
```

## License

`@gravewright/sdk` is licensed under MIT. `@gravewright/kernel` is licensed under Apache-2.0. Third-party modules remain under their respective licenses.

See [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes and
[SECURITY.md](SECURITY.md) to report vulnerabilities privately.
