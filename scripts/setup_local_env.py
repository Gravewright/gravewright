"""First-run local setup: create ``.env`` and generate a session secret.

Idempotent and safe to run repeatedly. The Windows and macOS/Linux installers
call this so non-technical users get a working local configuration without
editing files by hand:

* If ``.env`` is missing, it is created from ``.env.example`` or the canonical
  local-development template.
* If ``SESSION_SECRET`` is missing or still the development placeholder, a
  strong random value is generated so sessions are not signed with a shared
  default.

Only the Python standard library is used, so it runs anywhere.
"""

from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"
DEVELOPMENT_EXAMPLE = ROOT / ".env.development.example"
PLACEHOLDER_SECRETS = {"", "dev-only-change-me", "change-me"}
LOCAL_SQLITE_ENV = """# Gravewright local Windows configuration.
APP_NAME=Gravewright
APP_ENV=development
APP_DEBUG=false
DEFAULT_LOCALE=en
PUBLIC_BASE_URL=http://localhost:8000
ALLOWED_HOSTS=localhost,localhost:8000,127.0.0.1,127.0.0.1:8000
GRAVEWRIGHT_DATA_DIR=./data
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
ALLOW_SQLITE_IN_PRODUCTION=false
SESSION_SECRET=dev-only-change-me
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
"""


def main() -> int:
    if not ENV.exists():
        source = EXAMPLE if EXAMPLE.exists() else DEVELOPMENT_EXAMPLE
        if source.exists():
            ENV.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"created .env from {source.name}")
        else:
            ENV.write_text(LOCAL_SQLITE_ENV, encoding="utf-8")
            print("created .env with local SQLite defaults")

    lines = ENV.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = changed = False
    for line in lines:
        if line.startswith("SESSION_SECRET="):
            found = True
            value = line.split("=", 1)[1].strip()
            if value in PLACEHOLDER_SECRETS:
                out.append(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
                changed = True
                continue
        out.append(line)

    if not found:
        out.append(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
        changed = True

    if changed:
        ENV.write_text("\n".join(out) + "\n", encoding="utf-8")
        print("generated a unique SESSION_SECRET")
    else:
        print("SESSION_SECRET already set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
