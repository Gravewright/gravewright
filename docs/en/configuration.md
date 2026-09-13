# Configuration

[Documentation](../README.md) · [Português](../pt-BR/configuration.md)

## Loading and validation

The source of truth is [config/environment.py](../../config/environment.py), [config/engine.py](../../config/engine.py), [config/settings.py](../../config/settings.py) and [.env.example](../../.env.example). Settings load once at process startup. Exported variables take precedence over `.env`; interpolation is disabled, so `${VALUE}` remains literal. Relative paths resolve against the source root; `~` expands to the service user's home.

Booleans accept `1/true/yes/y/on` and `0/false/no/n/off`, case-insensitively. Invalid spellings fail startup. Engine numeric limits must be positive. Join-code minimum ≤ default ≤ maximum, and viewport area cannot exceed width × height. `GRAVEWRIGHT_PORT` must be 1–65535. Public origins normalize the scheme and hostname to lowercase, preserving explicit ports and IPv6 brackets; `HTTPS://VTT.EXAMPLE.COM` therefore enables the same HTTPS settings as `https://vtt.example.com`. They reject paths, trailing slashes, credentials, empty ports, control characters, query strings and fragments, including empty `?` or `#` delimiters. These validations do not imply that every setting has the same numeric parser or upper bound.

The [Windows runner](windows-runner.md) has a separate configuration flow: defaults from `.env.example`, then `%LOCALAPPDATA%\Gravewright\data\.env`, with local security and storage settings enforced by its dedicated profile. It does not load the source checkout's `.env`. The reference below describes the standard server settings; feature settings also apply to the runner, while its bind address, database/media paths, debug, cookies, host/origin, proxy trust and single-process Channels choices are fixed for local execution. Set the runner's port in its personal `.env`.

## Environment reference

Values below match the sample/default configuration. An empty cell shown as “empty” means no configured value. Byte values use binary units in explanations.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GRAVEWRIGHT_HOST` | `127.0.0.1` | Launcher bind address; main.py only |
| `GRAVEWRIGHT_PORT` | `3000` | Launcher port, 1–65535; main.py only |
| `DJANGO_DEBUG` | `true` | Django debug mode; false requires private secret and Redis in standard server settings |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost,[::1]` | Comma-separated hosts, without scheme or port |
| `GRAVEWRIGHT_PUBLIC_ORIGIN` | empty | Public HTTP(S) origin; pins the WebSocket origin/Host including port, adds host and CSRF trusted origin, enables Secure cookies for HTTPS |
| `GRAVEWRIGHT_DATABASE` | `data/gravewright.sqlite3` | SQLite filename; relative to source root; :memory: is supported |
| `GRAVEWRIGHT_MEDIA_ROOT` | `data/media` | Private upload/module storage, relative to source root |
| `GRAVEWRIGHT_AUTH_MAX_ATTEMPTS` | `30` | Authentication attempts per client-IP window |
| `GRAVEWRIGHT_AUTH_WINDOW_SECONDS` | `300` | Authentication window in seconds |
| `GRAVEWRIGHT_REDIS_URL` | empty | Channels Redis URL; standard server settings allow empty/in-memory delivery only in debug |
| `APP_NAME` | `Gravewright` | Fallback product name; persisted host preferences can override |
| `DEFAULT_LOCALE` | `en` | Fallback locale; current supported host locale is en |
| `PRIVACY_ENABLED` | `false` | Initial privacy publication setting; the saved Privacy checkbox takes precedence |
| `CAMPAIGN_JOIN_CODE_ENABLED` | `true` | Enable campaign join-code workflow |
| `CAMPAIGN_CLONE_ENABLED` | `true` | Enable campaign cloning |
| `CAMPAIGN_SNAPSHOTS_ENABLED` | `true` | Enable campaign snapshots |
| `CAMPAIGN_SNAPSHOT_RETENTION` | `20` | Maximum retained snapshots per campaign; pruned during snapshot creation |
| `ADMINISTRATIVE_AUDIT_ENABLED` | `true` | Enable administrative audit records |
| `ADMINISTRATIVE_AUDIT_RETENTION_DAYS` | `180` | Audit retention in days; pruning occurs when audit code runs |
| `TARGETED_HANDOUTS_ENABLED` | `true` | Enable targeted journal/handout sharing |
| `CAMPAIGN_EXPORT_ENABLED` | `true` | Enable portable campaign exports |
| `JOIN_CODE_DEFAULT_EXPIRES_HOURS` | `168` | Default join-code lifetime in hours |
| `JOIN_CODE_MIN_EXPIRES_HOURS` | `1` | Minimum requested join-code lifetime in hours |
| `JOIN_CODE_MAX_EXPIRES_HOURS` | `720` | Maximum requested join-code lifetime in hours |
| `JOIN_CODE_MAX_USES_LIMIT` | `1000` | Upper limit for a join code's allowed uses |
| `JOIN_CODE_REDEEM_MAX_ATTEMPTS` | `10` | Maximum code redemption attempts per window |
| `JOIN_CODE_REDEEM_WINDOW_SECONDS` | `600` | Code redemption attempt window in seconds |
| `TRUSTED_PROXIES` | empty | Comma-separated proxy IPs/CIDRs trusted for forwarded client IPs and ASGI HTTP/WebSocket schemes; empty ignores forwarding headers |
| `DATABASE_POOL_TIMEOUT` | `30` | SQLite lock wait in seconds; this is not a connection pool size |
| `DATABASE_ECHO` | `false` | Configure django.db.backends debug logging; actual SQL capture also follows Django's debug cursor behavior |
| `WS_MAX_MESSAGE_BYTES` | `65536` | Application limit per WebSocket message in bytes |
| `WS_COMMANDS_PER_SECOND` | `20` | WebSocket command rate per connection |
| `WS_BURST_COMMANDS` | `40` | WebSocket command burst capacity |
| `APP_DEBUG` | `false` | Application/table renderer diagnostics; independent of DJANGO_DEBUG |
| `COMMAND_PALETTE_ENABLED` | `true` | Enable the table command palette |
| `LOBBY_READY_CHECK_ENABLED` | `true` | Enable lobby readiness controls |
| `DYNAMIC_LIGHTING_ENABLED` | `true` | Enable dynamic-lighting feature |
| `SCENE_VIEWPORT_MAX_WIDTH_CHUNKS` | `16` | Maximum streamed viewport width in chunks |
| `SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS` | `16` | Maximum streamed viewport height in chunks |
| `SCENE_VIEWPORT_MAX_AREA_CHUNKS` | `256` | Maximum streamed viewport area in chunks |
| `FOG_MAX_OPS_PER_COMMAND` | `64` | Maximum fog operations per command |
| `FOG_MAX_POLYGON_POINTS` | `128` | Maximum points per fog polygon |
| `FOG_MAX_COORDINATE_ABS` | `100000` | Maximum absolute fog coordinate |
| `FOG_REQUIRE_EXPECTED_VERSION` | `true` | Require expected scene-state version for fog changes |
| `TOKEN_CREATE_MANY_MAX` | `50` | Maximum tokens per batch creation command |
| `BOARD_MARKERS_MAX_PER_SCENE` | `500` | Maximum markers per scene |
| `BOARD_MEASUREMENTS_MAX_PER_USER` | `50` | Maximum persisted board measurements per user |
| `JOURNAL_IMAGE_MAX_BYTES` | `10485760` | Journal image attachment limit in bytes (10 MiB) |
| `JOURNAL_PDF_MAX_BYTES` | `26214400` | Journal PDF attachment limit in bytes (25 MiB) |
| `GRAVEWRIGHT_MAP_MAX_PIXELS` | `64000000` | Decoded map pixel limit |
| `MAP_UPLOAD_MAX_BYTES` | `53687091200` | Map upload byte limit (50 GiB); other limits still apply |
| `MAP_IMAGE_MAX_WIDTH` | `500000` | Maximum source map width in pixels |
| `MAP_IMAGE_MAX_HEIGHT` | `500000` | Maximum source map height in pixels |
| `MAP_MAX_TILE_COUNT` | `4096` | Maximum generated map tiles |
| `GRAVEWRIGHT_MARKETPLACE_URL` | empty | HTTPS URL of the module catalog JSON |
| `GRAVEWRIGHT_MARKETPLACE_KEYS_FILE` | empty | Local Ed25519 trust-key JSON path; relative to source root |
| `GRAVEWRIGHT_RELEASES_REPOSITORY` | `Gravewright/gravewright` | owner/repo used for compatible Django release discovery; empty leaves it unconfigured |

Two optional commented settings are also recognized:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Development-only insecure fallback | Set a persistent random private value outside debug mode; do not use the fallback in production |
| `DJANGO_SECURE_COOKIES` | `false` | Enable secure cookies; a configured HTTPS public origin always enables them. This flag does not configure TLS or the WebSocket origin |

`GRAVEWRIGHT_CONTAINER` is read by release discovery to label the install format when set to `1`, `true` or `yes`; it does not configure a container runtime or provide automatic updates. `DJANGO_SETTINGS_MODULE` selects the Python settings module; entry points default to `config.settings`.

## Settings without environment switches

The following are configured in Python, not loaded automatically from similarly named `.env` entries:

| Setting | Current behavior |
| --- | --- |
| `DATABASES.default.TEST.NAME` | `data/test-gravewright.sqlite3`, regardless of `GRAVEWRIGHT_DATABASE` |
| `GRAVEWRIGHT_HEARTBEAT_SECONDS` / `GRAVEWRIGHT_PRESENCE_TTL` | 5-second heartbeat / 20-second presence TTL |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 8 MiB for Django request-data handling; not a universal uploaded-file byte cap |
| `SESSION_COOKIE_AGE` | 12 hours; session data is stored in the database |
| `TIME_ZONE` | `America/Sao_Paulo`, with timezone-aware datetimes |
| `STATIC_ROOT` | Source-root `staticfiles/` |
| `GRAVEWRIGHT_CONTENT_ROOT` | Optional Django settings override used by the content catalog; fallback is `data/vtt/compendiums/`. Merely exporting this name in `.env` has no effect |
| `MAILERS.default` | Console email backend |

Authentication bodies are separately limited to 16 KiB in middleware. Archive imports/exports have limits in `gravewright/administration/archives.py`. Map uploads have independent byte, decoded-image and generated-tile bounds. Check the owning code before assuming one limit governs every path.

## Persisted host preferences

`gravewright.administration.preferences` stores app identity, update channels and privacy content in the `HostSettings` singleton. `APP_NAME` and `DEFAULT_LOCALE` provide fallbacks, not forced overrides of every saved value. The supported locale list is currently `('en',)`. Setting `DEFAULT_LOCALE=pt-BR` does not add a Portuguese UI.

Privacy publication is enabled when either the environment flag or the stored privacy flag is true. Snapshot/audit retention is enforced by the relevant operation paths, not a background scheduler supplied by this project. User preferences and campaign settings are separate from these host settings.

For HTTPS, set the exact browser-facing public origin, including any non-default port. Other entries in `DJANGO_ALLOWED_HOSTS` do not become additional permitted WebSocket origins when a public origin is configured. Without it, WebSocket validation derives the origin from the ASGI scheme and Host; an absent scheme defaults to HTTP.

The [ASGI proxy adapter](../../config/proxy.py) accepts exactly one `X-Forwarded-Proto` header with value `http` or `https` only from the immediate socket peer in `TRUSTED_PROXIES`. It ignores duplicate, comma-separated, malformed or untrusted values. Keep Daphne's `--proxy-headers` disabled so the original peer remains available for this check. The same trust list controls [client-IP forwarding](../../gravewright/accounts/client_ip.py). See [deployment](deployment.md) for a TLS proxy example, Redis and storage requirements.
