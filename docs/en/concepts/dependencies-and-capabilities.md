# Dependencies and capabilities

Gravewright supports two relationships because they answer different questions.

## Concrete dependencies

Use `dependencies` when a module needs another module by exact identity:

```ts
dependencies: { "dice-roller": "^1.2.0" }
```

Only then may its factory call `ctx.use("dice-roller")`. Transitive dependencies
do not grant access: if A depends on B and B depends on C, A cannot use C unless
A declares C itself.

## Replaceable capabilities

Use `requires` when the consumer needs a versioned protocol but should not name
the implementation:

```ts
requires: { "gravewright.storage": "^1.0.0" }
```

A provider declares:

```ts
provides: { "gravewright.storage": "1.1.0" }
```

The consumer calls `ctx.capability("gravewright.storage")`. The activation plan
must find exactly one active, compatible provider. Recipes can select the
provider explicitly, making a distribution reproducible.

## Decision rule

- Use a dependency for a named collaborator with a module-specific API.
- Use a capability for a replaceable protocol with multiple implementations.
- Never use a transitive dependency as an implicit permission.

Marketplace installation resolves and installs missing concrete dependencies in
topological order, but it reports the dependency graph before proceeding and
does not activate the installed modules.
