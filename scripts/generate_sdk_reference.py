"""Generate the SDK capability/method-gate tables in the docs from source of truth.

The canonical source for capabilities is ``app/engine/sdk/capabilities.json``: it
owns the allow-list, the forbidden set, each capability's status, and the browser
method gates (``capability -> methods``). The docs must never drift from it, so
the structured tables in ``capabilities.md`` (EN and PT-BR) are generated here
between ``<!-- BEGIN GENERATED: <name> -->`` / ``<!-- END GENERATED -->`` markers.

Human-readable capability descriptions live in per-language sidecars under
``docs/<lang>/.../sdk/_data/capability-descriptions.json``. A capability without a
description is an error: adding a capability forces documenting it.

Usage:
    uv run python scripts/generate_sdk_reference.py            # write the docs
    uv run python scripts/generate_sdk_reference.py --check    # fail on drift (CI)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CAPABILITIES_JSON = PROJECT_ROOT / "app" / "engine" / "sdk" / "capabilities.json"

# Per-language doc targets. Headers differ per language; generated rows do not.
LANGUAGES = {
    "en": {
        "capabilities_md": PROJECT_ROOT / "docs" / "sdk" / "capabilities.md",
        "reference_md": PROJECT_ROOT / "docs" / "sdk" / "reference.md",
        "descriptions": PROJECT_ROOT / "docs" / "sdk" / "_data" / "capability-descriptions.json",
        "headers": {
            "allowed": ("Capability", "Purpose"),
            "gates": ("SDK method", "Required capability"),
        },
    },
    "pt-br": {
        "capabilities_md": PROJECT_ROOT / "docs" / "pt-br" / "sdk" / "capabilities.md",
        "reference_md": PROJECT_ROOT / "docs" / "pt-br" / "sdk" / "reference.md",
        "descriptions": PROJECT_ROOT
        / "docs"
        / "pt-br"
        / "sdk"
        / "_data"
        / "capability-descriptions.json",
        "headers": {
            "allowed": ("Capability", "Finalidade"),
            "gates": ("Método do SDK", "Capability exigida"),
        },
    },
}


class GenerationError(RuntimeError):
    """Raised when the docs cannot be generated from the current sources."""


# --- source parsing ---------------------------------------------------------


def parse_capabilities() -> tuple[set[str], set[str], dict[str, str]]:
    """Return (known capabilities, forbidden capabilities, method->capability).

<<<<<<< HEAD
    The method gate table documents the stable SDK 1 browser surface: only
    capabilities that declare ``methods`` contribute gate rows, while every
    capability is counted as known for the allow-list table.
=======
    The method gate table documents the *shipping* browser surface, so
    experimental capabilities (storage/bus, wired into the frontend in later
    phases) are excluded from the gate map but still counted as known.
>>>>>>> origin/main
    """
    data = json.loads(CAPABILITIES_JSON.read_text(encoding="utf-8"))
    capabilities = data.get("capabilities", {})
    if not capabilities:
        raise GenerationError(f"no capabilities parsed from {CAPABILITIES_JSON.name}")

    known = set(capabilities)
    forbidden = set(data.get("forbidden", {}))
    if not forbidden:
        raise GenerationError(f"no forbidden capabilities in {CAPABILITIES_JSON.name}")

    method_to_capability: dict[str, str] = {}
    for name, entry in capabilities.items():
<<<<<<< HEAD
=======
        if entry.get("status") == "experimental":
            continue
>>>>>>> origin/main
        for method in entry.get("methods", []) or []:
            method_to_capability[method] = name
    if not method_to_capability:
        raise GenerationError("no method gates parsed from capabilities.json")
    return known, forbidden, method_to_capability


# --- rendering --------------------------------------------------------------


def _table(header: tuple[str, str], rows: list[tuple[str, str]]) -> str:
    lines = [f"| {header[0]} | {header[1]} |", "|---|---|"]
    lines.extend(f"| {left} | {right} |" for left, right in rows)
    return "\n".join(lines)


def render_blocks(
    *,
    known: set[str],
    forbidden: set[str],
    method_to_capability: dict[str, str],
    descriptions: dict[str, str],
    headers: dict[str, tuple[str, str]],
) -> dict[str, str]:
    missing = sorted(cap for cap in known if cap not in descriptions)
    if missing:
        raise GenerationError(
            "capabilities without a description (add them to the sidecar): "
            + ", ".join(missing)
        )

    allowed_rows = [(f"`{cap}`", descriptions[cap]) for cap in sorted(known)]
    gate_rows = [
        (f"`sdk.{method}`", f"`{cap}`")
        for method, cap in sorted(method_to_capability.items())
    ]
    forbidden_block = "```text\n" + "\n".join(sorted(forbidden)) + "\n```"

    return {
        "allowed-capabilities": _table(headers["allowed"], allowed_rows),
        "forbidden-capabilities": forbidden_block,
        "method-gates": _table(headers["gates"], gate_rows),
    }


def replace_block(text: str, name: str, content: str) -> str:
    begin = f"<!-- BEGIN GENERATED: {name} -->"
    end = "<!-- END GENERATED -->"
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    if not pattern.search(text):
        raise GenerationError(f"marker '{name}' not found")
    return pattern.sub(f"{begin}\n{content}\n{end}", text)


# --- driver -----------------------------------------------------------------


def _process_language(lang: str, sources: dict, *, check: bool) -> list[str]:
    known, forbidden, method_to_capability = sources["capabilities"]
    config = LANGUAGES[lang]

    descriptions = json.loads(config["descriptions"].read_text(encoding="utf-8"))
    blocks = render_blocks(
        known=known,
        forbidden=forbidden,
        method_to_capability=method_to_capability,
        descriptions=descriptions,
        headers=config["headers"],
    )

    drift: list[str] = []
    target = config["capabilities_md"]
    text = target.read_text(encoding="utf-8")
    updated = text
    for name, content in blocks.items():
        updated = replace_block(updated, name, content)

    if updated != text:
        rel = target.relative_to(PROJECT_ROOT)
        if check:
            drift.append(str(rel))
        else:
            target.write_text(updated, encoding="utf-8")
            print(f"updated {rel}")

    # Soft anti-drift: every gated method must be documented in reference.md.
    reference = config["reference_md"].read_text(encoding="utf-8")
    undocumented = sorted(
        method for method in method_to_capability if f"sdk.{method}" not in reference
    )
    if undocumented:
        rel = config["reference_md"].relative_to(PROJECT_ROOT)
        raise GenerationError(
            f"{rel} is missing gated methods: " + ", ".join(undocumented)
        )

    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated docs differ from disk (do not write)",
    )
    args = parser.parse_args(argv)

    try:
        sources = {"capabilities": parse_capabilities()}
        drift: list[str] = []
        for lang in LANGUAGES:
            drift.extend(_process_language(lang, sources, check=args.check))
    except GenerationError as exc:
        print(f"ERROR  {exc}", file=sys.stderr)
        return 1

    if args.check and drift:
        print(
            "ERROR  generated docs are out of date: "
            + ", ".join(drift)
            + "\nFIX    run: uv run python scripts/generate_sdk_reference.py",
            file=sys.stderr,
        )
        return 1

    if args.check:
        print("SDK reference docs are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
