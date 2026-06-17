# Security Model

Gravewright is a server-authoritative multiplayer application. Clients submit intent; the server validates identity, role, permission, payload size, and domain rules before mutating state.

## Authentication

- Sessions are server-side.
- CSRF protection applies to unsafe form routes.
- Login, registration, and password reset flows are rate-limited.
- Production requires a strong session secret and secure cookie settings.

## Authorization

Campaign access is role-based:

```text
gm
assistant_gm
player
streamer
```

`PermissionService` is the central campaign permission entry point. Resource-level permissions exist for actors, items, journals, and table actions. GMs are privileged for their campaigns.

## WebSocket Security

The `/game/ws` endpoint validates:

- authenticated session;
- campaign membership;
- origin policy;
- maximum message size;
- command rate limits;
- payload shape;
- command-specific permissions.

Synchronous repository work reached from async realtime handlers should use `run_blocking(...)` so blocking database calls do not freeze the event loop.

## Upload Security

Map, actor, and journal image uploads are bounded by byte size, dimensions, content type, extension, and decoder validation. Scene uploads are tiled and chunked into local storage under validated IDs.

## Module Package Security

Module ZIP uploads are treated as untrusted:

- ZIP only;
- package size and entry count limits;
- path traversal rejected;
- absolute paths rejected;
- Windows drive prefixes rejected;
- symlink entries rejected;
- manifest required and validated before promotion;
- declared asset paths only.

## System Package Security

System manifests are declarative. They authorize assets, schemas, layouts, mappings, rules, locales, and content packs. Paths must be package-relative and safe. Unknown or forbidden capabilities make a package invalid.

## Production Checklist

- HTTPS only.
- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `WEB_WORKERS=1`.
- PostgreSQL database.
- Strong `SESSION_SECRET`.
- Explicit `PUBLIC_BASE_URL`.
- Explicit `ALLOWED_HOSTS`.
- Explicit `WS_ALLOWED_ORIGINS`.
- Secure, HTTP-only cookies.
- Backups for database and file storage.
- Owner-only diagnostics protected by normal authentication and ownership checks.
