# Security Policy

Gravewright is a multiplayer application that handles sessions, user-generated content, uploaded images, WebSocket commands, and installable extension packages. Security reports are welcome.

## Supported Versions

The project is pre-1.0. Security fixes target the current main development line unless a maintained release branch exists.

## Reporting a Vulnerability

Report vulnerabilities privately to the project maintainers. Include:

- affected version or commit;
- deployment mode and database backend;
- exact reproduction steps;
- expected impact;
- logs or proof of concept, with secrets removed.

Do not include real session cookies, passwords, reset tokens, private campaign data, or uploaded private assets.

## Security Scope

Relevant areas include:

- authentication and session handling;
- CSRF and unsafe HTTP methods;
- WebSocket origin checks, rate limits, command validation, and authorization;
- campaign permissions and role escalation;
- uploaded map, actor, and journal image handling;
- module ZIP extraction and asset serving;
- system and module manifest path traversal;
- private scene tile and journal asset access;
- production configuration hardening.

## Operational Baseline

Production deployments should use HTTPS, a strong `SESSION_SECRET`, explicit `ALLOWED_HOSTS`, `SESSION_COOKIE_SECURE=true`, `APP_DEBUG=false`, and PostgreSQL. The application refuses unsafe production defaults where possible.
