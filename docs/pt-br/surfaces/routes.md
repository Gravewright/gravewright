# Routes

`routes` associa um mount HTTP a um handler final exportado.

```ts
routes: { "/characters": "characters" },
exports: { get: ["characters"] },
```

```ts
characters(request: BaseRequest, response: BaseResponse) {
  response.json({ characters: [] });
}
```

Módulos usam `BaseRequest` e `BaseResponse`, neutros de transporte. O server ativo adapta para Express, Fastify ou outra implementação.

O handler precisa estar em `exports.get` e ser uma função. Mounts vazios e routes finais duplicadas são rejeitados. A composição ocorre antes do start e é removida pelo disposer do registrar.

## GET e POST no mesmo handler neutro

```ts
async characters(request: BaseRequest, response: BaseResponse) {
  if (request.method === "GET") return response.json({ characters: await repository.list() });
  if (request.method === "POST") {
    const body = request.body as { name?: unknown };
    if (typeof body?.name !== "string") return response.status(400).json({ error: "invalid_name" });
    return response.status(201).json(await repository.create(body.name));
  }
  response.status(405).json({ error: "method_not_allowed" });
}
```

O módulo continua responsável por validar `body`, `query` e headers não confiáveis. Neutralidade de transporte não significa validação de input.
