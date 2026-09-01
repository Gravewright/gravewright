# Gravewright documentation

[Português](../pt-br/README.md) · [Project README](../../README.md)

Gravewright is a TypeScript microkernel for composing a virtual tabletop from
independently versioned modules. This manual is organized by task: learn the
model, build a small working module, explore a subsystem, or look up an exact
contract.

## Choose your path

| If you want to… | Start here |
| --- | --- |
| Understand what Gravewright is | [Introduction](about/introduction.md) |
| Run the repository for the first time | [Getting started](getting-started/README.md) |
| Build your first module | [Your first module](getting-started/first-module.md) |
| Understand the architecture | [Core concepts](concepts/README.md) |
| Solve a specific authoring problem | [Guides](guides/README.md) |
| Look up an SDK or kernel boundary | [Reference](reference/README.md) |
| Diagnose a failure | [Troubleshooting](troubleshooting.md) |

## Documentation sections

- **Getting started** is sequential. It takes a new author from checkout to a
  validated module.
- **Core concepts** explains the reasoning behind modules, kinds, manifests,
  capabilities, composition, and lifecycle.
- **Guides** are task-oriented and can be read independently.
- **Reference** describes exact commands, schemas, and runtime surfaces.
- **Examples and templates** contain code intended to run, copy, and modify.

## Important invariants

- A running project has exactly one active `server`.
- `room` and `ruleset` are optional singletons (`0..1`); `addon` and `backend`
  are plural (`0..n`).
- `read`, `write`, and `stat` are optional administrative tooling.
- A module may use a concrete module only when it declares that dependency.
- Static manifests are validated before module code is imported.
- Installation never activates a module implicitly.

## Code resources

- [Minimal templates](../minimal-templates/README.md)
- [Complete examples](../examples/README.md)
- [Complete module-authoring guide](creating-a-module.md)

If the documentation and runtime disagree, treat that as a bug. Please open an
issue with the page, the command you ran, and the observed output.
