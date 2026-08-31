# Module kinds

Kinds define architectural roles and minimum contracts. Modules implement those roles; their internals remain opaque to Gravewright.

| Kind | Minimum contract | Active cardinality |
| --- | --- | --- |
| `server` | `start`, `stop`, `http`, `route`, `middleware`; optional `realtime` | exactly 1 |
| `room` | `mount`, `unmount`, `slots` and the canonical room slots | exactly 1 |
| `ruleset` | no universal game API | exactly 1 |
| `chat` | `send`, `erase` | 0..1 |
| `dice-engine` | `roll` | 0..1 |
| `assets` | `store`, `resolve`, `mimeTypeAllowed`, `remove` | 0..1 |
| `storage` | `create`, `find`, `where`, `update`, `delete` | 0..1 |
| `backend` | free exports | 0..N |
| `addon` | free exports | 0..N |

Use `dependencies` with `ctx.use()` when implementation identity matters, `uses` with `ctx.kind()` for a replaceable architectural role, and `requires`/`provides` with `ctx.capability()` for an optional semantic protocol that does not justify a kind.

`server` owns transport, routes and middleware. `room` owns the visual lifecycle and slots. `ruleset` deliberately has no universal character, combat, initiative or dice API.
