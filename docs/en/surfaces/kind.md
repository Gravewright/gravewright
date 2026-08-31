# `ctx.kind()`

`ctx.kind(kind)` resolves the active implementation of an architectural role. Declare every access in the consumer manifest:

```json
{ "uses": { "chat": "optional", "storage": "required" } }
```

```ts
const chat = ctx.kind("chat");       // ModuleRef<ChatKindAPI> | undefined
const storage = ctx.kind("storage"); // ModuleRef<StorageKindAPI>
const addons = ctx.kind("addon");    // readonly ModuleRef[]
```

Calling an undeclared kind is rejected. A missing required kind invalidates the activation plan. A missing optional singleton returns `undefined`; an optional plural kind returns an empty array. Kind relations participate in ordering, cycle detection, activation and disable validation.

Use `ctx.use()` for a concrete named dependency and `ctx.capability()` for a semantic protocol that is not an architectural role.
