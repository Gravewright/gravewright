# Routes

`routes` maps an HTTP mount to an exported final handler.

```ts
routes: { "/characters": "characters" },
exports: { get: ["characters"] },
```

```ts
characters(request: BaseRequest, response: BaseResponse) {
  response.json({ characters: [] });
}
```

Modules use transport-neutral `BaseRequest` and `BaseResponse`; the active server adapts them to Express, Fastify, or another implementation.

The handler name must exist in `exports.get` and resolve to a function. Empty mounts and duplicate final routes are rejected. Routes are composed before the server starts and removed through the disposer returned by the server registrar.

## GET and POST in one neutral handler

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

The module validates untrusted `body`, `query`, and headers itself. Transport neutrality is not input validation.
