# Middleware

`middleware` maps a mount to an ordered list of exported chain handlers.

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

Call `next()` exactly when processing should continue. Sending a response ends the chain. Each name must be unique within the mount, exported through `get`, and resolve to a function.

The kernel preserves module order and declaration order. Middleware is composed before routes.

## Authentication and audit chain

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

If `authenticate` sends `401`, it does not call `next()` and neither `audit` nor the route runs.
