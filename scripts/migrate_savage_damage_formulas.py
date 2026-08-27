#!/usr/bin/env python3
"""Migrate legacy Savage damage notation to the Gravewright formula DSL.

This is deliberately a data migration, not runtime coercion. After migration,
the rules engine receives only explicit calls to its native ``explode()``.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile


LEGACY_FORMULA = re.compile(
    r"^\s*(?:\d*)d\d+(?:\s*[+-]\s*(?:(?:\d*)d\d+|\d+))*\s*$",
    re.IGNORECASE,
)
DIE = re.compile(r"(?<![A-Za-z0-9_])(\d*)d(\d+)(?![A-Za-z0-9_])", re.IGNORECASE)
STRENGTH_PREFIX = re.compile(r"^\s*(?:for(?:ça)?|strength)\s*\+\s*", re.IGNORECASE)


def migrate_formula(value: object) -> tuple[object, bool, bool]:
    """Return ``(formula, changed, includes_strength)`` for known legacy forms."""
    if not isinstance(value, str) or not value.strip():
        return value, False, False
    source = value.strip()
    includes_strength = bool(STRENGTH_PREFIX.match(source))
    source = STRENGTH_PREFIX.sub("", source)
    if "explode(" in source.lower() or "acing(" in source.lower():
        return source, source != value, includes_strength
    if not LEGACY_FORMULA.fullmatch(source):
        return value, False, includes_strength

    def replace(match: re.Match[str]) -> str:
        count = int(match.group(1) or 1)
        sides = int(match.group(2))
        return " + ".join(f"explode({sides}, {sides})" for _ in range(count))

    migrated = DIE.sub(replace, source)
    return migrated, migrated != value, includes_strength


def migrate_document(document: dict) -> tuple[int, list[str]]:
    changed = 0
    unresolved: list[str] = []
    data = document.get("data") if isinstance(document.get("data"), dict) else document
    for collection in ("weapons", "powers"):
        for item in data.get(collection, []) if isinstance(data.get(collection), list) else []:
            item_data = item.get("data") if isinstance(item, dict) else None
            if not isinstance(item_data, dict):
                continue
            before = item_data.get("damage")
            after, did_change, includes_strength = migrate_formula(before)
            if includes_strength:
                item_data["addStrength"] = True
            if did_change:
                item_data["damage"] = after
                changed += 1
            elif isinstance(before, str) and before.strip() and not (
                "explode(" in before.lower() or "acing(" in before.lower()
            ):
                unresolved.append(f"{item.get('name') or item.get('id')}: {before}")
    if changed and isinstance(document.get("version"), int):
        document["version"] += 1
        document["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return changed, unresolved


def write_atomic(path: Path, document: dict) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(document, handle, ensure_ascii=False, separators=(",", ":"))
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("storage/system-data/savage-worlds"),
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    total = 0
    unresolved: list[str] = []
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for path in sorted(args.root.rglob("*.json")):
        if ".bak-" in path.name:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        changed, pending = migrate_document(document)
        unresolved.extend(f"{path}: {entry}" for entry in pending)
        if not changed:
            continue
        total += changed
        print(f"{'migrate' if args.apply else 'would migrate'} {path}: {changed}")
        if args.apply:
            shutil.copy2(path, path.with_name(f"{path.name}.bak-damage-{stamp}"))
            write_atomic(path, document)
    print(f"damage formulas: {total}; unresolved: {len(unresolved)}")
    for entry in unresolved:
        print(f"unresolved {entry}")
    return 0 if not unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
