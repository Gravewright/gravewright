# `read`, `write`, and `stat`

Every module publishes these POSIX-inspired commands through `exports.get`.

- `read(resource)` returns a resource owned by the module.
- `write(resource, value)` requests a validated change.
- `stat(resource?)` returns lightweight metadata or current status.

Resource names and return values belong to each module's documented API. A storage
system might expose `read("campaigns/42")`; a server might return
`{ running: true, port: 3000 }` from `stat()`. These are callable commands in
`exports.get`, not direct assignments in `exports.set`.
