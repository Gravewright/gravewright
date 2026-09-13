# Deployment and backups

[Documentation](../README.md) · [Português](../pt-BR/deployment.md)

This guide covers server deployments. For a Windows installation used only on its own computer, use the separate [Gravewright Runner](windows-runner.md), which manages personal storage and a single-process local profile.

## HTTPS and WebSockets

Gravewright supports HTTPS pages and secure WebSockets (WSS). Set `GRAVEWRIGHT_PUBLIC_ORIGIN` to the browser-facing origin, such as `https://vtt.example.com`. [SameOriginWebSocketMiddleware](../../gravewright/realtime/security.py) uses that configured origin to validate the browser's `Origin` and the request's `Host`, including the effective port. This also works with Daphne **4.2.3**, whose WebSocket scope omits `scheme`.

Behind a TLS-terminating reverse proxy, [TrustedProxySchemeMiddleware](../../config/proxy.py) restores the HTTP/HTTPS or WS/WSS scheme before the ASGI router handles the request. It accepts exactly one `X-Forwarded-Proto: http` or `https` header only when the socket peer belongs to `TRUSTED_PROXIES`. Untrusted, duplicate, comma-separated or malformed values leave the original scheme unchanged. This lets Django correctly recognize HTTPS for CSRF checks and HSTS responses.

The public origin is an allowlist, not a TLS listener or permission grant. Table WebSockets still require an allowed host, one valid matching browser origin, a valid session and campaign authorization. With no configured public origin, WebSocket checks use the ASGI `ws`/`wss` scheme; an omitted scheme defaults to local HTTP. Direct TLS with Daphne therefore requires the public HTTPS origin. `DJANGO_SECURE_COOKIES=true` alone does not supply it.

## Runtime configuration

Run from a versioned source checkout as an account that can write the configured database and private storage. Use a persistent, private `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, an explicit allowed-host list, the intended public origin and a Redis URL. A public origin must be an HTTP(S) origin with no path or trailing slash. HTTPS enables secure session/CSRF cookies and HSTS in settings.

Generate a secret locally and put it in protected configuration, preserving it across restarts:

```bash
uv run --locked python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Do not paste the generated value into an issue, commit or shared log. See [configuration](configuration.md) for limits, paths and environment precedence.

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python manage.py migrate --noinput
uv run --locked --no-dev python manage.py collectstatic --noinput
uv run --locked --no-dev python manage.py check --deploy
uv run --locked --no-dev daphne -b 127.0.0.1 -p 3000 config.asgi:application
```

These commands assume production values have already been set and storage directories exist. `check --deploy` can report settings requiring an operator decision; verify the public endpoint as described below as well. The last command binds plain HTTP to loopback behind the TLS proxy. `main.py` invokes Django's development `runserver`; `config.wsgi` cannot serve WebSockets.

## Nginx reverse proxy

For Nginx and Daphne on the same host, configure these values in protected application configuration, together with your private `DJANGO_SECRET_KEY`:

```dotenv
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=vtt.example.com
GRAVEWRIGHT_PUBLIC_ORIGIN=https://vtt.example.com
TRUSTED_PROXIES=127.0.0.1/32
GRAVEWRIGHT_REDIS_URL=redis://127.0.0.1:6379/0
```

Use the loopback Daphne command above **without `--proxy-headers`**. That option rewrites the socket peer before Gravewright checks it and conflicts with application-managed proxy trust. `TRUSTED_PROXIES` controls both forwarded client-IP resolution and the ASGI scheme adapter. Trust only the proxy addresses that can connect to Daphne; keep its upstream port private. In a container topology, replace loopback with the actual immediate proxy address or a narrowly scoped trusted network.

The following Nginx example belongs inside its `http` context. Replace the domain, existing certificate/key files and absolute checkout path before enabling it. The 100 MiB request-body limit is an example operational limit; size it for your uploads and server capacity. The TLS directives and WebSocket upgrade handling follow the [Nginx HTTPS guide](https://nginx.org/en/docs/http/configuring_https_servers.html) and [WebSocket proxy guide](https://nginx.org/en/docs/http/websocket.html).

```nginx
map $http_upgrade $gravewright_connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name vtt.example.com;
    return 308 https://vtt.example.com$request_uri;
}

server {
    listen 443 ssl;
    server_name vtt.example.com;

    ssl_certificate /etc/letsencrypt/live/vtt.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vtt.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 100m;

    location /static/ {
        alias /srv/gravewright/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $gravewright_connection_upgrade;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Forwarded "";
        proxy_set_header X-Forwarded-Host "";
        proxy_set_header X-Forwarded-Port "";
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

`Host $http_host` preserves the browser-facing port; Nginx passes `Origin` through unchanged. The proxy overwrites the trusted forwarding values rather than appending client-supplied data. See [Nginx proxy header configuration](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header). For a public port other than 443, include it in `GRAVEWRIGHT_PUBLIC_ORIGIN`, the TLS listener and redirect target. `DJANGO_ALLOWED_HOSTS` contains hostnames without ports.

Nginx handles the HTTP-to-HTTPS redirect; this checkout does not enable Django's global SSL redirect. Install a valid certificate and arrange renewal, validate the configuration with `nginx -t`, then reload Nginx through your service manager. After configuration changes, verify login, Secure session/CSRF cookies, HSTS on an application response and an authenticated table connection with status `101` over WSS. Check two browser sessions and rejection of a foreign WebSocket origin. The automated direct-TLS and proxy regression is documented in [testing](testing.md).

## Static files and private storage

Serve `/static/` from the `staticfiles/` directory produced by `collectstatic`. Runtime app assets, including frontend modules served by custom views, still need their corresponding application routes. With debug disabled, Django does not automatically serve collected files through the development static handler.

Keep `MEDIA_ROOT` private: uploaded maps, PDFs, journal files, audio, cards and installed module packages are served by guarded routes. A public `/media/` alias would bypass these checks. Back up private storage together with the database. Optional disk compendium collections in `data/vtt/compendiums/` need backup too.

Configure upstream upload limits and timeouts explicitly for your deployment. The default map byte limit is 50 GiB, while decoded-pixel, dimension and tile limits apply separately; a high accepted byte limit does not imply that the server can process such a file within available memory.

## Multiple processes

All workers need the same database, media files, secret, module trust configuration and Redis channel layer. Standard server settings require `GRAVEWRIGHT_REDIS_URL` with debug disabled, even for one process. The dedicated local runner is a separate profile and cannot be used for this deployment. In-memory Channels cannot exchange events between workers.

SQLite is the configured database engine and uses `IMMEDIATE` transactions. Redis provides event delivery, not a replacement database or durable record of gameplay. Multiple ASGI processes still share SQLite's write contention; the source does not supply a PostgreSQL configuration or claim horizontally distributed storage support. Size deployments based on observed workloads.

Use a service manager to supervise ASGI and Redis, retain logs, and shut down gracefully. Test two browser sessions, player/GM visibility, uploads, WebSocket reconnection and worker restarts after any hosting change.

## Backups and restoration

Campaign exports are portable content packages; snapshots are campaign recovery points. Neither is a full instance backup. Exports omit or sanitize some memberships, ownership and private session history, and module installation state is outside their content graph. See [archives.py](../../gravewright/administration/archives.py).

For a consistent full backup:

1. Stop application writes, including every ASGI process and any maintenance process.
2. Copy the configured SQLite database and associated journal/WAL files if present, all private media, optional content collections, and required configuration/trust-key files. A SQLite backup operation is also suitable for the database, but it must be coordinated with the media snapshot.
3. Keep the matching source version, lock file and licenses with the backup record. Protect secrets separately and restrict access to the backup.
4. Restore into a separate directory first, with the same configuration paths adjusted for that environment. Verify login, a campaign, representative uploads and installed modules before switching traffic.

Do not copy only `db.sqlite3` in the source root or restore older code over a newer migrated database. Test a rollback using a matching database/media backup rather than assuming migrations can be reversed.

## Updates and optional services

Core update discovery is opt-in through `GRAVEWRIGHT_RELEASES_REPOSITORY=owner/repo`. It expects compatible Django release artifacts with SHA-256 metadata. The current updater reports status and artifact information; it does not replace the running installation. Verify downloaded bytes, back up, review migrations and perform source upgrades manually.

Marketplace configuration uses an HTTPS catalog and a local file of trusted Ed25519 public keys. An empty URL leaves online discovery unconfigured. Review module authors and code before installation because modules execute on the application's origin. See [modules](modules.md).

Mail currently uses Django's console backend. Privacy text and publication settings are operator-managed content; enabling a flag does not supply a completed privacy policy or an operational email service. Dependency, Redis-server, browser and container-image licenses must also be considered for the actual distributed deployment; see [third-party notices](../../THIRD_PARTY_NOTICES.md).

### In-app updates on Windows, Linux and macOS

Normal `main.py` and Gravewright Runner launches now enable the supervisor by
default. Windows users keep starting `Gravewright Runner.bat`; Linux/macOS
source installations use `uv run --locked python main.py`. Only developers
need `--dev` for autoreload. No special update mode is required.

Use Administration → Updates → **Back up and install update** on all three
platforms. The interface controls download, SHA-256 validation, isolated
locked dependencies, backup, migrations, restart and failure recovery. Alpha
releases use Development. Active table connections briefly disconnect during
the swap; the administration page polls for the restarted server.

Releases require a higher version, the supervisor files, and a
`Gravewright-VERSION-django.zip` asset with a GitHub SHA-256 digest. The default
repository is `Gravewright/gravewright`; an explicitly empty value disables
discovery. The legacy initial `0.1.0-alpha.0` release predates the supervisor;
that old installation must first receive the updated launcher to support
in-app installation.

New code lives separately from the original checkout. SQLite, media,
compendiums and the Runner's shared static files are backed up and restored
on migration/startup failure. Interrupted transactions recover at next launch.
Dirty Git checkouts are protected. Never run another server against the same
database during a swap.

Runner updates live under its user-data `updates` directory. `main.py` uses
`%LOCALAPPDATA%/Gravewright/updates` on Windows,
`~/Library/Application Support/Gravewright/updates` on macOS, or
`$XDG_STATE_HOME/gravewright/updates` (default `~/.local/state/gravewright/updates`)
on Linux. Preserve these directories and reserve disk space: backups are not
automatically removed.

The `Automatic updates` workflow runs native Windows/Linux/macOS tests. Run
`uv run python tests/e2e/automatic_updates.py` and the same command with
`--runner` for isolated HTTPS upgrades and deliberate migration/startup failures.
