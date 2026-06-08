# Contributing to Gravewright

Gravewright welcomes focused contributions that improve reliability, performance, security, documentation, and the public extension APIs.

## Development Setup

```bash
uv sync
cp .env.example .env
uv run uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Before Opening a Pull Request

Run the checks that match your change:

```bash
uv run pytest tests/unit
python3 -m compileall app tests scripts main.py
docker compose -f tests/docker-compose.perf.yml config
```

Use focused test runs while developing. Broaden the run when touching shared services, persistence, realtime transport, permissions, scene streaming, or public APIs.

## Engineering Standards

- Keep HTTP handlers in `app/actions`.
- Keep product rules in `app/business`.
- Keep table-runtime behavior in `app/engine`.
- Keep persistence in `app/persistence/repositories`.
- Do not make `actions` import repositories directly.
- Do not make `engine` depend on Litestar request or response objects.
- Treat the backend as authoritative for game state.
- Keep public extension APIs documented before relying on them from systems or modules.

## Licensing of Contributions

Unless explicitly stated otherwise, contributions to the core are submitted under Apache-2.0. Contributions to API materials are submitted under MIT. See `docs/licensing.md`.

## Security Issues

Do not open a public issue for a vulnerability. Follow `SECURITY.md`.
