# Dependencies

`dependencies` maps concrete module names to SemVer ranges.

```ts
dependencies: {
  "dice-roller": "^1.0.0",
  "event-log": "~2.3.0",
}
```

Dependencies serve three distinct stages:

1. The marketplace resolves missing modules from catalogs and installs the graph in topological order.
2. The kernel validates presence, active state, and compatible versions before factories run.
3. `ctx.use()` authorizes communication only with declared names.

An already installed compatible version is reused. Missing catalog entries, incompatible versions, and cycles abort installation before commit. Installation does not activate modules automatically.

Depend on the smallest stable public API possible. A dependency is a product-level coupling decision, even when the kernel keeps the mechanism clean.

## Transitive installation example

```text
combat-ui 1.0.0
└── combat ^2.0.0
    ├── dice-roller ^1.2.0
    └── event-log ~3.1.0
```

Installing `combat-ui` produces this plan:

```text
dice-roller → event-log → combat → combat-ui
```

If `event-log 3.1.4` is already installed, it is reused and omitted from downloads. If `event-log 4.0.0` is installed, the operation stops with an incompatibility instead of replacing it silently.

```ts
dependencies: {
  combat: "^2.0.0",
}
```

The manifest uses module names as keys; URLs remain marketplace catalog concerns.
