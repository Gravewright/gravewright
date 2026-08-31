# `ctx.kind()`

`ctx.kind(kind)` resolve a implementação ativa de um papel arquitetural. Declare todo acesso no manifest do consumidor:

```json
{ "uses": { "chat": "optional", "storage": "required" } }
```

```ts
const chat = ctx.kind("chat");       // ModuleRef<ChatKindAPI> | undefined
const storage = ctx.kind("storage"); // ModuleRef<StorageKindAPI>
const addons = ctx.kind("addon");    // readonly ModuleRef[]
```

O acesso a um kind não declarado é rejeitado. A ausência de um kind obrigatório invalida o plano. Um singleton opcional ausente retorna `undefined`; um kind plural opcional retorna array vazio. Relações por kind participam da ordem, detecção de ciclos, ativação e validação de disable.

Use `ctx.use()` para dependência concreta por nome e `ctx.capability()` para um protocolo semântico que não é papel arquitetural.
