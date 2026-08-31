# Getting started

This section is a sequential introduction. By the end, you will have run the
host, generated a module, validated its static artifacts, and understood where
to go next.

## Prerequisites

- Node.js 24 or newer
- npm
- Git
- A terminal in the repository root

## 1. Install and verify

```bash
npm install
npm run typecheck
npm test
printf '{\n  "gravewright-server": "active",\n  "gravewright-marketplace": "active"\n}\n' > gravewright.modules.json
npm run grave -- doctor
```

The repository does not commit a distribution's module-state choice. The local
file above activates the included server and marketplace system. `doctor` checks
that configuration and the manifests without modifying the workspace. Fix any
reported error before starting the host.

## 2. Run the host

```bash
npm run grave -- run
```

The kernel discovers installed modules, reads their requested states, plans the
complete active graph, constructs modules, composes contributions, and starts
the single active server. Stop it with `Ctrl+C`; shutdown runs in reverse order.

For an audit file of semantic actions:

```bash
npm run grave -- run --diagnostic
```

## 3. Build something

Continue with [Your first module](first-module.md). For a longer explanation of
every authoring step, use the [complete module guide](../creating-a-module.md).

## What this tutorial does not assume

It does not require Express, React, PixiJS, or SQLite. A module owns its npm
dependencies and imports them normally; the kernel does not install arbitrary
framework packages for every project.
