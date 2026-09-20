# Django server modules

Default folder for trusted Django apps installed by the host operator.
Configured by `GRAVEWRIGHT_DJANGO_MODULES_ROOT` in `.env`; `config/settings.py`
appends it to `sys.path`, so a package placed directly in this folder only needs
its import path listed in `GRAVEWRIGHT_SERVER_APPS`:

```
extensions/django/my_app/__init__.py
extensions/django/my_app/apps.py
```

```
GRAVEWRIGHT_SERVER_APPS=my_app
```

Explicit `GRAVEWRIGHT_SERVER_APP_PATHS` entries are still supported for
checkouts kept elsewhere, and they take precedence over this folder. An
`AppConfig` may expose `gravewright_urlconf` to append URL patterns.

These apps run as trusted server code: they must enforce authentication, CSRF
and the native domain permissions. They are never populated from browser package
manifests, and their Python dependencies still require separate installation. An
invalid app import prevents startup instead of silently disabling the app.

Folder contents are ignored by git, so third-party apps stay outside this
repository's history.

See `docs/en/modules.md` ("Explicitly installed Django apps").
