# Creating a Gravewright module

[Português](../pt-br/criando-um-modulo.md) · [Minimal templates](../minimal-templates/README.md) · [Example](../examples/dice-roller/README.md)

This guide covers the complete lifecycle of a module: scaffolding, implementation, typing, composition, validation, and release.

For contract-level details, use the [public surfaces reference](surfaces/README.md).

## 1. Choose a kind

Kinds describe a module's role. They do not select an implementation or grant hidden privileges.

| Kind | Intended role |
| --- | --- |
| `server` | Host transport, routes, middleware, and slots |
| `room` | Complete campaign and table interface |
| `ruleset` | Game rules and resolution |
| `addon` | Optional extension of other modules |
| `system` | Backend service such as storage, realtime, assets, or marketplace |

Every running project has exactly one active `server`. Every other kind is optional
and supports multiple active implementations.

`room` owns the campaign interface, including its renderer and components.
`system` owns backend capabilities. `ruleset` owns game rules, checks, combat,
conditions, and resolution.

## 2. Generate the scaffold

From the project root:

```bash
npm run grave -- new addon fog-of-war
```

If `grave` is installed globally:

```bash
grave new addon fog-of-war
```

The name is normalized to lowercase kebab-case. The command creates:

```text
modules/fog-of-war/
├── manifest.json
├── package.json
├── index.ts
└── types.ts
```

Use `--example-complete` to include a README, a test, and a diagnostic event:

```bash
grave new addon fog-of-war --example-complete
```

New modules are not activated automatically.

Each module owns its Node dependencies in `package.json`. Import the package
normally from the module that uses it; the kernel does not load or know that
dependency. Commit the module's `package-lock.json`; marketplace installation
requires it and runs `npm ci --omit=dev --ignore-scripts`.

## 3. Implement the module

`index.ts` defines metadata, composition points, exports, and the instance factory:

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "fog-of-war",
  kind: "addon",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["read", "write", "stat", "reveal", "isRevealed"] },
  create(ctx) {
    const revealed = new Set<string>();

    return {
      read(area: string) { return revealed.has(area); },
      write(area: string, value: unknown) { value ? revealed.add(area) : revealed.delete(area); },
      stat() { return { revealed: revealed.size }; },
      reveal(area: string) {
        revealed.add(area);
        ctx.diagnostic.record({
          event: "fog.revealed",
          actor: "System",
          action: "Reveal map area",
          status: "success",
          details: { area },
        });
      },
      isRevealed(area: string) {
        return revealed.has(area);
      },
    };
  },
});
```

`create()` runs when the kernel activates the module. Keep imports free of side effects: do not open ports, connect to databases, or start timers at module evaluation time.

The returned object is the module instance. Only names declared under `exports` can cross the module boundary.

## 4. Declare exports

```ts
exports: {
  get: ["read", "write", "stat", "roll", "reset", "status"],
}
```

- `get` is the only public surface. It exposes readable values and callable commands.
- Mutations are explicit commands such as `configure()`, `setTheme()`, or `write()`.

An export must exist on the object returned by `create()` and cannot be duplicated.

## 5. Generate the manifest and types

Use the module definition as the authoring source, then generate the static artifacts:

```bash
grave module build modules/fog-of-war
```

Verify that generated files are current in CI:

```bash
grave module build modules/fog-of-war --check
```

A generated manifest looks like this:

```json
{
  "name": "fog-of-war",
  "kind": "addon",
  "provider": "community",
  "version": "0.1.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "exports": {
    "get": ["read", "write", "stat", "reveal", "isRevealed"]
  }
}
```

The manifest is intentionally duplicated as a static artifact. The kernel validates it before importing module code.

## 6. Register the TypeScript API

Generated `types.ts` infers the public API and registers the exact module name:

```ts
import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type FogOfWarAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "fog-of-war": FogOfWarAPI;
  }
}
```

Run the workspace type registry sync:

```bash
npm run types:sync
npm run typecheck
```

Consumers now receive the inferred API instead of `unknown`:

```ts
const fog = ctx.use("fog-of-war");
fog.get("reveal")("north-wing");
const visible = fog.get("isRevealed")("north-wing");
```

## 7. Use another module

Declare dependencies before calling `ctx.use()`:

```ts
export default defineModule({
  name: "dice-log",
  kind: "addon",
  provider: "community",
  version: "1.0.0",
  dependencies: {
    "dice-roller": "^1.0.0",
  },
  exports: { get: ["read", "write", "stat", "rollAndLog"] },
  create(ctx) {
    const dice = ctx.use("dice-roller");
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat() { return { ready: true }; },
      rollAndLog() {
        return dice.get("roll")(20);
      },
    };
  },
});
```

The kernel validates presence, activation state, compatible SemVer, and initialization order. Depending on a module by kind is not supported: dependencies name the concrete module they consume.

For a replaceable contract, declare `requires`, let an implementation declare
`provides`, and call `ctx.capability(name)`. A recipe selects the concrete provider.
Missing, incompatible, or ambiguous providers fail during planning, before factories run.

Register external resources immediately:

```ts
const timer = setInterval(flush, 1_000);
ctx.onDispose(() => clearInterval(timer));
```

Cleanup runs in reverse order after failed creation, disable, and `kernel.shutdown()`.

When this module is installed from the marketplace, Gravewright resolves missing dependencies by name from the configured catalogs. It validates every SemVer constraint, rejects cycles and incompatible installed versions, then prepares and installs the graph in topological order: dependencies first, requested module last. Installation does not activate modules automatically.

## 8. Compose routes, middleware, and slots

Modules can expose values for the active server without depending on Express or another framework:

```ts
import { defineModule, type BaseRequest, type BaseResponse } from "@gravewright/sdk";

export default defineModule({
  name: "character-sheet",
  kind: "system",
  provider: "community",
  version: "1.0.0",
  routes: { "/characters": "characters" },
  exports: { get: ["read", "write", "stat", "characters"] },
  create(_ctx) {
    return {
      read(_resource: string) { return []; },
      write(_resource: string, _value: unknown) {},
      stat() { return { characters: 0 }; },
      characters(_request: BaseRequest, response: BaseResponse) {
        response.json({ characters: [] });
      },
    };
  },
});
```

Composition fields map mount or slot names to exports:

```ts
routes: { "/characters": "characters" },
middleware: { "/characters": ["authenticate", "audit"] },
slots: { "gw-toolbar": ["toolbarButton"] },
```

Every referenced value must also be present in `exports.get`. Registrars return disposers so the kernel can reverse composition during rollback or disable.

## 9. Diagnostics

Diagnostics are opt-in and semantic. Record public names and actions, not secrets or raw payloads:

```ts
ctx.diagnostic.record({
  event: "dice.rolled",
  actor: "Player",
  action: "Roll d20",
  status: "success",
  details: { sides: 20, result: 10 },
});
```

`status` describes whether the software action succeeded, not whether the RPG roll succeeded. Run with:

```bash
grave run --diagnostic
```

Do not record tokens, session IDs, private paths, request bodies, or personal information.

## 10. Activate and validate

Set the desired state in `gravewright.modules.json`:

```json
{
  "gravewright-server": "active",
  "fog-of-war": "active"
}
```

Then validate the project:

```bash
npm run types:sync
npm run typecheck
npm test
npm run grave -- doctor
npm run grave -- run
```

`grave doctor` reports malformed manifests, state problems, missing dependencies,
invalid room protocols, capability-provider conflicts, and invalid server configurations.

## 11. Test the capability

Test public behavior rather than implementation details:

```ts
import assert from "node:assert/strict";
import test from "node:test";

test("roll stays inside the requested die", () => {
  const result = Math.floor(Math.random() * 6) + 1;
  assert.ok(result >= 1 && result <= 6);
});
```

Modules should also test failure paths, disposer behavior, dependency calls, and manifest drift.

## 12. Publish a release

Marketplace installation uses releases, not the repository's `main` branch.

1. Build a ZIP containing `manifest.json` and the module entry.
2. Create an immutable versioned release.
3. Calculate the ZIP SHA-256 digest.
4. Publish a stable manifest URL such as `latest.json`.
5. Submit that URL to the marketplace catalog.

The remote manifest adds release fields:

```json
{
  "name": "fog-of-war",
  "kind": "addon",
  "provider": "community",
  "version": "1.0.0",
  "entry": "./index.js",
  "exports": { "get": ["read", "write", "stat", "reveal", "isRevealed"] },
  "download_url": "https://example.org/releases/fog-of-war-1.0.0.zip",
  "download_sha256": "64-lowercase-or-uppercase-hexadecimal-characters"
}
```

The stable manifest may point to a newer release later. A published ZIP must remain immutable.

## Checklist

- The name is lowercase kebab-case and matches its directory and registry key.
- The version is valid SemVer.
- Every `ctx.use()` target appears in `dependencies`.
- Every exposed or composed value is explicitly declared.
- Importing the module causes no external side effects.
- `types.ts` augments `ModuleRegistry` with a quoted name.
- `grave module build --check`, typecheck, tests, and doctor pass.
- Release ZIP and SHA-256 are immutable and correspond to the remote manifest.
