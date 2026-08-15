# Configuration

Gravewright reads environment variables through `app/config.py`. Environment files are loaded according to `APP_ENV`, and local `.env` values can override shared defaults.

## Environment Modes

```text
development
staging
production
test
```

Production mode performs strict startup validation and fails fast on unsafe settings.

## Versioned templates

| File | Intended use |
| --- | --- |
| `.env.example` | Minimal local quick-start template copied to `.env`. |
| `.env.development.example` | Development defaults loaded when `APP_ENV=development`. |
| `.env.staging.example` | Staging defaults and placeholders. |
| `.env.production-postgresql.example` | Recommended production baseline using PostgreSQL. |
| `.env.production-sqlite.example` | Small, private, single-server production installs. Copy it to `.env` explicitly. |

Only `.env` contains private deployment values. Files ending in `.example` are
sanitized templates and must never contain real credentials.

## Core Settings

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment. |
| `APP_DEBUG` | Enables debug behavior. Must be false in production. |
| `WEB_WORKERS` | Uvicorn worker count. Must be 1 in production for V1 realtime correctness. |
| `PUBLIC_BASE_URL` | Canonical external URL. Must be HTTPS in production. |
| `ALLOWED_HOSTS` | Comma-separated accepted hosts. Required in production. |
| `TRUSTED_PROXIES` | Comma-separated proxy IPs or CIDRs. |
| `WS_ALLOWED_ORIGINS` | Explicit WebSocket origins. Derived from `ALLOWED_HOSTS` when empty. |
| `GRAVEWRIGHT_DATA_DIR` | SDK package data root. Defaults to `data/`. |
| `DATABASE_URL` | SQLAlchemy database URL. |

## Database Settings

Local default:

```env
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
```

Production should use PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/gravewright
```

SQLite production use is refused unless `ALLOW_SQLITE_IN_PRODUCTION=true` is set. MySQL/MariaDB is not a supported production backend in V1.

A genuinely empty database is initialized automatically through the full
Alembic migration history. `AUTO_MIGRATE=false` still blocks startup when an
existing database is behind the expected revision, protecting stored data from
implicit upgrades.

## Session Settings

| Variable | Purpose |
| --- | --- |
| `SESSION_SECRET` | Signing secret. Use at least 32 random characters in production. |
| `SESSION_MAX_AGE` | Session lifetime in seconds. |
| `SESSION_COOKIE_NAME` | Browser cookie name. |
| `SESSION_COOKIE_SECURE` | Must be true in production. |
| `SESSION_COOKIE_HTTPONLY` | Must be true in production. |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict`, or `none`. |
| `SESSION_COOKIE_DOMAIN` | Optional cookie domain. |

## Rate and Size Limits

Configuration includes positive integer limits for:

- auth attempts and password reset windows;
- WebSocket message size and command buckets;
- viewport chunk width, height, area, known chunks, and layer count;
- fog operation and coordinate limits;
- token batch creation;
- board markers and measurements;
- map upload bytes, image dimensions, tile size, and tile count.

All numeric limits must be greater than zero.

### Campaign join-code limits

| Variable | Default | Purpose |
| --- | ---: | --- |
| `CAMPAIGN_JOIN_CODE_ENABLED` | `true` | Enables join-code routes and GM/player interfaces. Set `false` for operational rollback. |
| `CAMPAIGN_EMAIL_INVITATION_CREATION_ENABLED` | `true` | Keeps creation of legacy email invitations available during the transition release. Disabling it does not invalidate pending invitations. |
| `COMMAND_PALETTE_ENABLED` | `true` | Enables campaign-scoped server search and the Ctrl/Cmd+K command palette. Existing panels remain available when disabled. |
| `CAMPAIGN_CLONE_ENABLED` | `true` | Enables the GM-only selective campaign clone wizard, preview, and creation endpoints. |
| `CAMPAIGN_SNAPSHOTS_ENABLED` | `true` | Enables GM-only campaign snapshot creation and restore. |
| `CAMPAIGN_SNAPSHOT_RETENTION` | `20` | Maximum retained snapshots per campaign, including automatic safety snapshots. |
| `ADMINISTRATIVE_AUDIT_ENABLED` | `true` | Enables persistent campaign administrative history and its GM-only UI/API. |
| `ADMINISTRATIVE_AUDIT_RETENTION_DAYS` | `180` | Retention window used by audit pruning operations. |
| `TARGETED_HANDOUTS_ENABLED` | `true` | Enables targeted journal, item, and library-image grants. Set `false` to hide the UI and return 404 from its endpoints. |
| `LOBBY_READY_CHECK_ENABLED` | `true` | Enables the campaign lobby, ready status, character selection, asset-state reporting, and realtime summary. |
| `CAMPAIGN_EXPORT_ENABLED` | `true` | Enables GM-only selective campaign package downloads. Set `false` to hide the UI and disable the endpoint. |
| `DYNAMIC_LIGHTING_ENABLED` | `true` | Enables scene walls, doors, and client-side line of sight. Set `false` to hide tools and disable wall endpoints. |
| `JOIN_CODE_DEFAULT_EXPIRES_HOURS` | `168` | Default lifetime (seven days). |
| `JOIN_CODE_MIN_EXPIRES_HOURS` | `1` | Shortest accepted lifetime. |
| `JOIN_CODE_MAX_EXPIRES_HOURS` | `720` | Longest accepted lifetime (30 days). |
| `JOIN_CODE_MAX_USES_LIMIT` | `1000` | Highest accepted `max_uses`. |
| `JOIN_CODE_REDEEM_MAX_ATTEMPTS` | `10` | Failed attempts allowed per user, IP, and combined key. |
| `JOIN_CODE_REDEEM_WINDOW_SECONDS` | `600` | Sliding failure-count window. |

All values must be positive, and the default expiration must remain between the
configured minimum and maximum. Successful redemption clears the corresponding
failure buckets. IP-derived rate-limit keys are hashed before persistence.

## Privacy Settings

`PRIVACY_ENABLED` controls whether the privacy panel and related settings are visible for the instance.
