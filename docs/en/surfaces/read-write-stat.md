# Optional administrative tooling

`read`, `stat`, and `write` are optional host/CLI integrations. They are not kind contracts, are not automatically listed in `exports.get`, and are never available through `Context`.

```json
{ "tooling": { "read": true, "stat": true, "write": true } }
```

- `read` feeds `grave help <module> [topic]` with structured documentation.
- `stat` feeds `grave doctor` with module-owned health information.
- `write` feeds `grave test [module]` with a self-test harness.

If an operation is declared, the module factory must implement it. These hooks are operational conveniences, not a sandbox or a module-to-module protocol.
