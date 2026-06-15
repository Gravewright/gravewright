# Security Policy

Gravewright is a multiplayer application that handles sessions, user-generated content, uploaded images, WebSocket commands, and installable SDK packages. Security reports are welcome.

## Supported Versions

The project is pre-1.0. Security fixes target the current main development line unless a maintained release branch exists.

## Reporting a Vulnerability

Report vulnerabilities privately to the project maintainers. Include:

- affected version or commit;
- deployment mode and database backend;
- exact reproduction steps;
- expected impact;
- logs or proof of concept, with secrets removed.

Do not include real session cookies, passwords, reset tokens, private campaign data, uploaded private assets, or private package content.

## Security Scope

Relevant areas include:

- authentication and session handling;
- CSRF and unsafe HTTP methods;
- WebSocket origin checks, rate limits, command validation, and authorization;
- campaign permissions and role escalation;
- uploaded map, actor, journal, and package asset handling;
- package manifest validation;
- package-relative path traversal;
- package asset serving;
- trusted JavaScript package entrypoints;
- SDK capability enforcement;
- package dependency/conflict activation checks;
- backup/restore safety;
- private scene tile and journal asset access;
- production configuration hardening.

## SDK Package Security

Gravewright packages are installed code/data. Declarative package data is validated. Scripted packages that declare `assets.scripts` run trusted JavaScript in the browser for users in the table.

Install scripted packages only from authors you trust.

The public SDK forbids capabilities such as:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

There is no backend plugin execution in SDK v1.

## Operational Baseline

Production deployments should use:

- HTTPS;
- a strong `SESSION_SECRET`;
- explicit `ALLOWED_HOSTS`;
- restricted `WS_ALLOWED_ORIGINS`;
- `SESSION_COOKIE_SECURE=true`;
- `APP_DEBUG=false`;
- PostgreSQL;
- tested backups and restore procedures.

The application refuses unsafe production defaults where possible.

## Alpha Data Safety

Gravewright Alpha does not guarantee an upgrade path. Before updating an instance with data you care about:

```bash
grave doctor
grave backup -o gravewright-backup.zip --include-assets --verify
```

Test restore on a copy before updating a real table.
