# Introduction

[Documentation home](../README.md) · [Português](../../pt-br/about/introducao.md)

Gravewright is an open-source foundation for building virtual tabletops. It is
not a finished tabletop, a renderer, or a rules engine. It is the small runtime
that validates and composes those parts.

## What problem does it solve?

VTT implementations often bind transport, campaign state, game rules, storage,
and presentation into one application. Replacing one part then means forking or
rewriting the whole stack. Gravewright gives each part an explicit module
boundary so a distribution can replace one implementation without changing the
kernel.

```text
project
├── exactly one server       transport and host integration
├── zero or more rooms       campaign/table experiences
├── zero or more rulesets    game mechanics
├── zero or more addons      optional extensions
└── zero or more systems     backend services
```

The kernel knows these five roles and their minimum contracts. It does not know
Express, SQLite, PixiJS, a specific game, or a particular marketplace.

## The two boundaries

A module has a static boundary and a runtime boundary:

1. `manifest.json` lets the host inspect identity, dependencies, capabilities,
   composition points, and public names before importing code.
2. `create(ctx)` constructs the instance only after the activation plan passes.

The manifest is a validation and composition boundary, not a security sandbox.
Installed JavaScript still runs with the permissions of the host process.

## What to read next

- New to the repository: [Getting started](../getting-started/README.md).
- Evaluating the design: [Architecture](../concepts/architecture.md).
- Ready to code: [Your first module](../getting-started/first-module.md).
- Looking for an exact API: [Reference](../reference/README.md).
