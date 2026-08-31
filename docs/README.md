# Gravewright documentation

Choose a language:

- [English](en/README.md)
- [Português do Brasil](pt-br/README.md)

Both manuals follow the same learning structure:

```text
docs/<language>/
├── about/             product and documentation overview
├── getting-started/   sequential first-run tutorial
├── concepts/          architecture and mental models
├── guides/            task-oriented procedures
├── reference/         exact CLI, manifest, and API contracts
└── surfaces/          one page per public runtime surface
```

Shared, executable resources live outside the translated manuals:

- [Minimal templates](minimal-templates/README.md) cover all five module kinds.
- [Examples](examples/README.md) demonstrate complete behavior and tests.

The structure is intentionally progressive: a new author should not need the
reference manual to finish the first tutorial, while an experienced author
should be able to reach an exact contract without reading introductory prose.
