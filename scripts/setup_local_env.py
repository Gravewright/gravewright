"""First-run local setup: create ``.env`` and generate a session secret.

Idempotent and safe to run repeatedly. The Windows and macOS/Linux installers
call this so non-technical users get a working local configuration without
editing files by hand:

* If ``.env`` is missing, it is created from ``.env.example``.
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
PLACEHOLDER_SECRETS = {"", "dev-only-change-me", "change-me"}


def main() -> int:
    if not ENV.exists():
        if not EXAMPLE.exists():
            print("ERROR  .env.example not found; cannot create .env")
            return 1
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print("created .env from .env.example")

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
