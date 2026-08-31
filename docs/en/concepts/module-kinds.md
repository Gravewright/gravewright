# Module kinds

Kinds describe architectural responsibility. Do not create a new kind for every
feature; choose the closest stable role.

| Kind | Responsibility | Cardinality | Minimum beyond `read`/`write`/`stat` |
| --- | --- | --- | --- |
| `server` | Transport, middleware, routes, slots, startup | exactly one active | `start`, `stop`, `route`, `middleware`, `slot` |
| `room` | Complete campaign/table interface | `0..n` | `mount`, `unmount`, room protocol and canonical slots |
| `ruleset` | Rules and mechanics of a game | `0..n` | none |
| `addon` | Optional extension to existing behavior | `0..n` | none |
| `system` | Backend service or infrastructure | `0..n` | none |

Examples of `system` modules include SQLite storage, localization, login
authorization, realtime synchronization, and a marketplace. These are features,
not reasons to grow the kind vocabulary.

A renderer that forms the campaign/table experience belongs to `room`.
Small optional controls that extend an existing room belong to `addon`.

Kinds do not authorize access. Concrete dependencies and public exports do.
