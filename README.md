# Gravewright

**Forge the world. Run the table.**

Gravewright is an extensible virtual tabletop built on a small modular kernel. The product is the VTT itself; the kernel is its internal modular infrastructure, the SDK is the public surface for implementations and modules, and modules extend Gravewright with infrastructure or product features.

> Project status: early development (`0.1.0`, pre-1.0). Gravewright currently provides the kernel, authoring SDK, CLI, and shared UI package. A runnable table also needs one active server, backend, and frontend implementation.

## Why Gravewright

- **Extensible VTT:** add game and product functionality through modules.
- **Composable infrastructure:** select server, backend, and frontend implementations independently.
- **Small public surfaces:** modules can access only declared dependencies and exports.
- **Predictable operation:** dependency planning, lifecycle ordering, rollback, and reverse-order cleanup are kernel responsibilities.
- **Deliberate evolution:** pre-1.0 breaking changes are documented and include migration guidance when reasonable.
- **Transport-neutral:** HTTP and realtime contracts do not require a specific server library; the kernel does not depend on the DOM.

## Product model

Every installation selects exactly one active implementation of each structural role:

| Role | Product responsibility |
| --- | --- |
| `server` | HTTP, middleware, routes, and optional realtime delivery |
| `backend` | Server-side application and persistence lifecycle |
| `frontend` | Makes the browser client available |
| `module` | Any number of game or product features |

Modules live under `modules/<name>/`, declare their public contract in `manifest.json`, and are enabled in `gravewright.modules.json`. They communicate through concrete `manifest.dependencies`, `ctx.use(moduleId)`, and public exports read with `ModuleRef.get(exportName)`.

## Get started

Requires Node.js 24 or newer.

```bash
npm ci
npm test
npm run typecheck
```

Create structural implementations and ordinary extensions with the CLI:

```bash
npm run grave -- new server my-server --minimal
npm run grave -- new backend my-backend --minimal
npm run grave -- new frontend my-frontend --minimal
npm run grave -- new module fog-of-war --example-complete
```

Review the generated code, mark the desired modules as `"active"` in `gravewright.modules.json`, then validate and run:

```bash
npm run grave -- doctor
npm run grave -- run --diagnostic
```

Scaffolds are intentionally disabled by default. `doctor` must report exactly one active structural implementation of every role before the runtime starts.

## Documentation

- [English documentation](docs/en/README.md)
- [Documentação em português](docs/pt-BR/README.md)
- [SDK governance / Governança do SDK](docs/SDK-GOVERNANCE.md)
- [Contributing / Como contribuir](CONTRIBUTING.md)
- [Support / Como pedir ajuda](SUPPORT.md)
- [Security policy / Política de segurança](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Packages

- `@gravewright/sdk` — authoring contracts and TypeScript helpers (MIT)
- `@gravewright/kernel` — validation, dependency planning, and lifecycle orchestration (Apache-2.0)
- `@gravewright/ui` — shared Vue primitives, tokens, and BEM styles (private)

---

## Português

Gravewright é um VTT extensível construído sobre um pequeno kernel modular. O produto é o próprio VTT; o kernel é sua infraestrutura modular interna, o SDK é a superfície pública para implementações e módulos, e os módulos são extensões do Gravewright.

Cada composição possui exatamente uma implementação estrutural `server`, uma `backend` e uma `frontend`. Extensões comuns usam `kind: "module"`. A comunicação entre módulos ocorre por dependências concretas declaradas em `manifest.dependencies`, resolvidas com `ctx.use()` e acessadas por exports públicos através de `ModuleRef.get()`.

O projeto está em desenvolvimento inicial (`0.1.0`, pré-1.0). Comece com `npm ci`, leia a [documentação em português](docs/pt-BR/README.md), crie as implementações estruturais, execute `npm run grave -- doctor` e inicie com `npm run grave -- run`.
