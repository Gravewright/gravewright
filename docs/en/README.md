# Gravewright documentation

[Português](../pt-br/README.md) · [Project README](../../README.md)

## Module authors

- [Creating a module](creating-a-module.md): the complete authoring workflow, manifest, SDK, types, dependencies, composition, diagnostics, testing, and releases.
- [Public surfaces](surfaces/README.md): one detailed page per SDK and kernel boundary.
- [Minimal templates](../minimal-templates/README.md): small foundations intended for copying.
- [Complete examples](../examples/README.md): documented, working module examples.

## Core concepts

- A module is an independently versioned capability.
- Its static `manifest.json` is the security and composition boundary.
- Its default export is created with `defineModule()`.
- Its public TypeScript API augments `ModuleRegistry` in `types.ts`.
- Modules are disabled unless explicitly marked `active` in `gravewright.modules.json`.
- Exactly one active module must implement the `server` kind.
