# Development

[Documentation](../README.md) · [Português](../pt-BR/development.md)

## Find the owning layer

Read [architecture](architecture.md) and the [code map](code-map.md) before changing a cross-domain flow. Domain `services.py` files own authorization, validation and persistence. Views translate HTTP requests and responses; WebSocket consumers translate incoming messages, while realtime dispatch publishes committed changes. Keep business rules in services so browser and Python entry points share the same checks.

Use the public [API](api.md) when integrating with the core. A Python context identifies a caller; it does not grant authorization. Direct ORM writes are appropriate for controlled migrations/fixtures but can bypass service permissions, revision checks, file cleanup and notifications in ordinary application code.

For mutations, examine the domain's transaction, request ID and expected-version conventions. Preserve retry behavior and publish committed state. Player and streamer snapshots must exclude hidden data on the server, not merely hide it in the DOM.

## Typical workflow

```bash
uv sync --locked
uv run --locked python main.py
```

Edit the owning service and its views/templates/frontend only as needed. Write a regression test for a changed rule or boundary, and run the relevant [test suites](testing.md). Documentation-only edits usually need link/example review and a focused check, rather than new tests that repeat prose.

For model changes:

```bash
uv run --locked python manage.py makemigrations
uv run --locked python manage.py migrate
uv run --locked python manage.py makemigrations --check --dry-run
```

Review generated migrations before applying them to valuable data. App labels and model names are also used by portable campaign archives. A schema change may require archive import/export and snapshot tests in addition to model tests.

## Browser contracts and assets

The browser registry is generated from `gravewright/modules/contracts/frontend.json`:

```bash
uv run --locked python scripts/generate_frontend_api.py
```

Commit the source contract and generated `gravewright/modules/static/gravewright_modules/frontend-contract.js` together. The separate SDK contract uses [contracts/registry.json](../../gravewright/modules/contracts/registry.json), [contracts/api.json](../../gravewright/modules/contracts/api.json) and the files in [contracts/schemas/](../../gravewright/modules/contracts/schemas/), including `manifest.json`. See [modules](modules.md) and [frontend](frontend.md) before changing them.

Frontend code is native JavaScript modules. Keep lifecycle cleanup explicit for listeners, timers, render objects and asynchronous work. Some third-party bundles have their own build metadata; rebuilding those is separate from launching the Django application. Preserve license banners and update [third-party notices](../../THIRD_PARTY_NOTICES.md) when replacing a bundle.

## Documentation conventions

English guides live under `docs/en/`; Portuguese guides use the same filename under `docs/pt-BR/`. Each guide links back to the index and to its translation. Use relative links so documentation works in forks and downloaded source trees. Do not embed a developer's absolute workspace paths or assume a repository URL that is not configured.

Explain why code exists, its responsibilities and constraints. Keep comments close to the boundary they explain. For important public functions, document accepted identifiers/payloads, return values, side effects and domain errors. Preserve concise existing explanations; do not add a redundant comment to every assignment.

The existing dice grammar documents are maintained next to their implementation. New project guides should link to those references rather than duplicate syntax rules that can drift.

## Release identifiers

The current release is **Alpha 0.1.0**. Its equivalent identifiers follow the formats required by each tool:

| Location | Identifier |
| --- | --- |
| Public release name, application and Runner | `Alpha 0.1.0` |
| Python project and `uv.lock` | `0.1.0a0` |
| Frontend package, package lock and update API | `0.1.0-alpha.0` |
| Release tag | `v0.1.0-alpha.0` |
| Source release artifact | `Gravewright-0.1.0-alpha.0-django.zip` |

[`pyproject.toml`](../../pyproject.toml) is the source of the installed version. [`gravewright/version.py`](../../gravewright/version.py) derives its public identifier and label; keep the frontend package metadata aligned when changing it. Python's [prerelease format](https://packaging.python.org/en/latest/specifications/version-specifiers/#pre-releases) and [Semantic Versioning](https://semver.org/) both distinguish this alpha from the later stable `0.1.0` release. API/SDK contract versions and third-party module versions have independent lifecycles.

The updater classifies alpha releases in the `dev` channel. The selected update channel remains a host preference; naming this release alpha does not change an existing preference or opt users into preview updates.

## Before submitting

Follow [CONTRIBUTING.md](../../CONTRIBUTING.md). Check translated docs, the generated registry, migrations and license notices as applicable. Describe the exact validation performed and any failures. Never include `.env`, runtime data, private uploads or test browser credentials from a real deployment.
