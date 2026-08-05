from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_ROOTS = (PROJECT_ROOT / "data",)


def iter_json_files() -> list[Path]:
    files: list[Path] = []
    for root in JSON_ROOTS:
        if root.exists():
            files.extend(sorted(root.rglob("*.json")))
    return files


def main() -> int:
    failures: list[tuple[Path, str]] = []

    for path in iter_json_files():
        try:
            with path.open("r", encoding="utf-8") as handle:
                json.load(handle)
        except Exception as exc:                                                                
            failures.append((path, str(exc)))

    if failures:
        print("JSON validation failed:", file=sys.stderr)
        for path, message in failures:
            rel = path.relative_to(PROJECT_ROOT)
            print(f"- {rel}: {message}", file=sys.stderr)
        return 1

    print(f"Validated {len(iter_json_files())} JSON files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
