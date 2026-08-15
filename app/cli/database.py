"""``grave db``: schema/migration diagnostics and the official upgrade path.

- ``grave db status`` reports the current revision, the expected head, and
  whether the database is up to date (JSON with ``--json``).
- ``grave db upgrade`` runs ``alembic upgrade head``: the supported way to
  create or evolve a database.
- ``grave db adopt`` verifies and adopts an unversioned legacy SQLite database.
"""

from __future__ import annotations

import argparse

from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK


def _status() -> dict:
    from app.persistence.engine import get_engine
    from app.persistence.schema import schema_status

    return schema_status(get_engine())


def cmd_status(args: argparse.Namespace) -> int:
    try:
        status = _status()
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        if getattr(args, "json", False):
            import json

            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        else:
            print(f"ERROR  could not read schema status: {type(exc).__name__}: {exc}")
            print("FIX    Check DATABASE_URL and database connectivity.")
        return EXIT_DOCTOR_ERROR

    if getattr(args, "json", False):
        import json

        print(json.dumps({"ok": True, **status}, indent=2, sort_keys=True))
    else:
        verdict = "up to date" if status["up_to_date"] else "OUT OF DATE"
        print(f"Backend:  {status['backend']}")
        print(f"Current:  {status['current'] or 'none (uninitialized)'}")
        print(f"Head:     {status['head']}")
        print(f"Status:   {verdict}")
        if not status["up_to_date"]:
            print("FIX       Back up, then run: grave db upgrade  (alembic upgrade head)")

    return EXIT_OK if status["up_to_date"] else EXIT_DOCTOR_ERROR


def cmd_upgrade(args: argparse.Namespace) -> int:
    from app.persistence.schema import schema_status, upgrade_to_head
    from app.persistence.engine import get_engine

    try:
        upgrade_to_head()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR  migration failed: {type(exc).__name__}: {exc}")
        print("FIX    Restore your backup and inspect the migration output.")
        return EXIT_DOCTOR_ERROR

    status = schema_status(get_engine())
    print(f"OK     database at head: {status['head']}")
    return EXIT_OK


def cmd_adopt(args: argparse.Namespace) -> int:
    from app.persistence.engine import get_engine
    from app.persistence.schema import adopt_legacy_database

    try:
        result = adopt_legacy_database(get_engine())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR  adoption refused: {type(exc).__name__}: {exc}")
        print("FIX    Inspect the reported drift; the database was not stamped.")
        return EXIT_DOCTOR_ERROR
    print(f"OK     adopted at revision: {result['revision']}")
    print(f"Backup: {result['backup']}")
    print(f"Schema fingerprint: {result['fingerprint']}")
    return EXIT_OK
