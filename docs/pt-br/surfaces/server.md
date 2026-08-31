# Contrato de server

`server` é o único kind com cardinalidade no projeto. Exatamente um módulo ativo deve implementá-lo.

Exports obrigatórios:

- `http` expõe a implementação HTTP concreta como valor opaco.
- `start()` — abre o listener após a composição.
- `stop()` — fecha recursos corretamente.
- `route(mount, handler)` — registra handler final e retorna disposer.
- `middleware(mount, handler)` — registra middleware e retorna disposer.
- `slot(name, value)` — registra extensão e retorna disposer.

O kernel exige que todos estejam em `get` e sejam funções. Ele não exige Express nem conhece o transporte.

`BaseRequest` e `BaseResponse` são uma surface neutra deliberadamente mínima
para routes e middleware básicos e portáveis. Elas não tentam representar todo
o HTTP. Um server concreto pode exportar APIs adicionais; um módulo que precise
de streaming, headers especializados ou recursos do framework pode depender
explicitamente da implementação, por exemplo
`ctx.use("gravewright-server").get("http")`.

`start()` é aguardado exatamente uma vez depois de middleware e routes. O server ativo não pode ser desabilitado durante a execução do kernel. Slots visuais pertencem à room.

## Comportamento mínimo de registrar

```ts
route(mount: string, handler: RouteHandler) {
  let active = true;
  adapter.register(mount, async (request, response, next) => {
    if (!active) return next();
    await handler(request, response);
  });
  return () => { active = false; };
}
```

O disposer retornado é obrigatório e usado em rollback e disable. Retornar nada viola o contrato mesmo que o registro inicial funcione.

```ts
async start() { listener = await adapter.listen({ host: "127.0.0.1", port: 3000 }); }
async stop() { await listener?.close(); listener = undefined; }
```
