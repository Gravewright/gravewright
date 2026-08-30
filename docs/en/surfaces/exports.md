# Exports

`exports` is the allowlist of values that may cross the module boundary.

```ts
exports: {
  get: ["roll", "configure"],
  prop: ["status"],
}
```

- `get`: readable values and callable commands.
- `prop`: readable/writable properties.
- `set`: deprecated writable-only compatibility surface.

Every name must exist on the runtime instance. Names must be unique and cannot overlap categories. A value returned by `create()` but omitted here remains private.

Prefer commands such as `configure(options)` over publishing mutable implementation state.

## Private versus public instance

```ts
exports: { get: ["findCharacter"] },
create(_ctx) {
  const database = new Map([["elly", { name: "Elly", hp: 12 }]]);
  function normalize(name: string) { return name.trim().toLowerCase(); }
  return {
    database, // returned but private: not declared
    normalize, // returned but private: not declared
    findCharacter(name: string) { return database.get(normalize(name)); },
  };
}
```

Consumers can obtain only `findCharacter`. Attempting `get("database")` is denied even though that property exists at runtime.
