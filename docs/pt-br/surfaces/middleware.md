# Middleware

`middleware` associa um mount a uma lista ordenada de handlers encadeados.

```ts
middleware: { "/campaign": ["authenticate", "audit"] },
exports: { get: ["authenticate", "audit"] },
```

```ts
authenticate(request, response, next) {
  if (!request.headers.authorization) return response.status(401).json({ error: "unauthorized" });
  next();
}
```

Chame `next()` somente quando o processamento deve continuar. Enviar uma resposta encerra a cadeia. Cada nome precisa ser único no mount, estar em `get` e resolver para uma função.

O kernel preserva a ordem dos módulos e a ordem declarada. Middleware é composto antes de routes.

## Cadeia de autenticação e auditoria

```ts
create(ctx) {
  return {
    authenticate(request, response, next) {
      const token = request.headers.authorization;
      if (token !== "Bearer public-example") return response.status(401).json({ error: "unauthorized" });
      next();
    },
    audit(request, _response, next) {
      ctx.diagnostic.record({ event: "http.request", actor: "User", action: `Access ${request.path}`, status: "success" });
      next();
    },
  };
}
```

Se `authenticate` enviar `401`, ele não chama `next()` e nem `audit` nem a route executam.
