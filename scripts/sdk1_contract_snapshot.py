"""Semantic fingerprint and breaking-change classifier for the SDK 1 contract.

The generated contract carries prose, ordering and formatting that may change
freely. What a package actually depends on is narrower: which methods exist, what
they require, what they return, and the shape of the DTOs involved. This module
reduces the contract to exactly that, and classifies any difference against the
frozen RC 1 baseline.

Usage::

    python scripts/sdk1_contract_snapshot.py --write   # re-freeze the baseline
    python scripts/sdk1_contract_snapshot.py --check   # fail on BREAKING drift
    python scripts/sdk1_contract_snapshot.py --diff    # print the classification
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "docs" / "sdk" / "_data" / "gravewright-sdk-1.json"
SNAPSHOT = PROJECT_ROOT / "docs" / "sdk" / "_data" / "gravewright-sdk-1.rc1-snapshot.json"

COMPATIBLE = "COMPATIBLE"
POTENTIALLY_BREAKING = "POTENTIALLY_BREAKING"
BREAKING = "BREAKING"


def fingerprint(contract: dict[str, Any]) -> dict[str, Any]:
    """Reduce a generated contract to the parts a package can depend on."""
    methods = {}
    for method in contract["methods"]:
        parameters = method.get("parameters") or []
        methods[method["path"]] = {
            "capability": method["requiredCapability"],
            "returns": method["returns"],
            "required": [p["name"] for p in parameters if p.get("required")],
            "optional": sorted(p["name"] for p in parameters if not p.get("required")),
            "types": {p["name"]: p.get("type") for p in parameters},
            "asynchronous": bool(method.get("asynchronous")),
        }

    dtos = {}
    for name, dto in contract["dtos"].items():
        properties = dto.get("properties") or {}
        dtos[name] = {
            "required": sorted(dto.get("required") or []),
            "fields": {key: value.get("typeExpression") for key, value in properties.items()},
            "additionalProperties": bool(dto.get("additionalProperties")),
        }

    return {
        "sdkVersion": contract["sdkVersion"],
        "methods": methods,
        "capabilities": sorted(item["name"] for item in contract["capabilities"]),
        "events": sorted(item["name"] if isinstance(item, dict) else item for item in contract["events"]),
        "errors": sorted(contract["errors"]),
        "dtos": dtos,
        "typeAliases": dict(contract.get("typeAliases") or {}),
    }


def _classify_methods(before: dict, after: dict, findings: list[dict]) -> None:
    for path in sorted(set(before) - set(after)):
        findings.append({"level": BREAKING, "kind": "method_removed", "subject": path})
    for path in sorted(set(after) - set(before)):
        findings.append({"level": POTENTIALLY_BREAKING, "kind": "method_added", "subject": path,
                         "detail": "structurally compatible; requires explicit RC feature review"})
    for path in sorted(set(before) & set(after)):
        old, new = before[path], after[path]
        if old["capability"] != new["capability"]:
            findings.append({"level": BREAKING, "kind": "method_capability_changed", "subject": path,
                             "detail": f"{old['capability']} -> {new['capability']}"})
        if old["returns"] != new["returns"]:
            findings.append({"level": BREAKING, "kind": "method_return_changed", "subject": path,
                             "detail": f"{old['returns']} -> {new['returns']}"})
        if old["asynchronous"] != new["asynchronous"]:
            findings.append({"level": BREAKING, "kind": "method_sync_changed", "subject": path})
        for name in new["required"]:
            if name not in old["required"]:
                findings.append({"level": BREAKING, "kind": "parameter_now_required",
                                 "subject": f"{path}({name})"})
        for name in old["required"]:
            if name not in new["required"] and name not in new["optional"]:
                findings.append({"level": BREAKING, "kind": "parameter_removed",
                                 "subject": f"{path}({name})"})
        for name in sorted(set(old["optional"]) - set(new["optional"]) - set(new["required"])):
            findings.append({"level": BREAKING, "kind": "optional_parameter_removed",
                             "subject": f"{path}({name})"})
        for name in sorted(set(new["optional"]) - set(old["optional"]) - set(old["required"])):
            findings.append({"level": COMPATIBLE, "kind": "optional_parameter_added",
                             "subject": f"{path}({name})"})
        for name in sorted(set(old["types"]) & set(new["types"])):
            if old["types"][name] != new["types"][name]:
                findings.append({"level": BREAKING, "kind": "parameter_type_changed",
                                 "subject": f"{path}({name})",
                                 "detail": f"{old['types'][name]} -> {new['types'][name]}"})


def _classify_dtos(before: dict, after: dict, findings: list[dict]) -> None:
    for name in sorted(set(before) - set(after)):
        findings.append({"level": BREAKING, "kind": "dto_removed", "subject": name})
    for name in sorted(set(after) - set(before)):
        findings.append({"level": COMPATIBLE, "kind": "dto_added", "subject": name})
    for name in sorted(set(before) & set(after)):
        old, new = before[name], after[name]
        for field in sorted(set(old["fields"]) - set(new["fields"])):
            findings.append({"level": BREAKING, "kind": "dto_field_removed", "subject": f"{name}.{field}"})
        for field in sorted(set(new["fields"]) - set(old["fields"])):
            level = BREAKING if field in new["required"] else COMPATIBLE
            findings.append({"level": level,
                             "kind": "dto_required_field_added" if level == BREAKING else "dto_field_added",
                             "subject": f"{name}.{field}"})
        for field in sorted(set(old["fields"]) & set(new["fields"])):
            if old["fields"][field] != new["fields"][field]:
                findings.append({"level": BREAKING, "kind": "dto_field_type_changed",
                                 "subject": f"{name}.{field}",
                                 "detail": f"{old['fields'][field]} -> {new['fields'][field]}"})
        for field in sorted(set(new["required"]) - set(old["required"]) - (set(new["fields"]) - set(old["fields"]))):
            findings.append({"level": BREAKING, "kind": "dto_field_now_required", "subject": f"{name}.{field}"})
        for field in sorted(set(old["required"]) - set(new["required"])):
            findings.append({"level": COMPATIBLE, "kind": "dto_field_now_optional", "subject": f"{name}.{field}"})


def classify(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every semantic difference, most severe first."""
    findings: list[dict[str, Any]] = []
    if before["sdkVersion"] != after["sdkVersion"]:
        findings.append({"level": BREAKING, "kind": "sdk_version_changed",
                         "subject": f"{before['sdkVersion']} -> {after['sdkVersion']}"})
    _classify_methods(before["methods"], after["methods"], findings)
    _classify_dtos(before["dtos"], after["dtos"], findings)
    for label, kind in (("capabilities", "capability"), ("events", "event"), ("errors", "error")):
        old, new = set(before[label]), set(after[label])
        for name in sorted(old - new):
            findings.append({"level": BREAKING, "kind": f"{kind}_removed", "subject": name})
        for name in sorted(new - old):
            level = POTENTIALLY_BREAKING if kind == "capability" else COMPATIBLE
            findings.append({"level": level, "kind": f"{kind}_added", "subject": name,
                             "detail": "requires explicit RC feature review" if level == POTENTIALLY_BREAKING else ""})
    for name in sorted(set(before["typeAliases"]) - set(after["typeAliases"])):
        findings.append({"level": BREAKING, "kind": "type_alias_removed", "subject": name})
    for name in sorted(set(before["typeAliases"]) & set(after["typeAliases"])):
        if before["typeAliases"][name] != after["typeAliases"][name]:
            findings.append({"level": BREAKING, "kind": "type_alias_changed", "subject": name})

    order = {BREAKING: 0, POTENTIALLY_BREAKING: 1, COMPATIBLE: 2}
    return sorted(findings, key=lambda item: (order[item["level"]], item["kind"], item["subject"]))


def current_fingerprint() -> dict[str, Any]:
    return fingerprint(json.loads(CONTRACT.read_text(encoding="utf-8")))


def baseline_fingerprint() -> dict[str, Any]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _dump(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="re-freeze the RC 1 baseline")
    parser.add_argument("--check", action="store_true", help="exit non-zero on BREAKING drift")
    parser.add_argument("--diff", action="store_true", help="print every classified difference")
    args = parser.parse_args(argv)

    current = current_fingerprint()
    if args.write:
        # An explicit LF keeps the frozen artifact byte-identical across platforms.
        SNAPSHOT.write_text(_dump(current), encoding="utf-8", newline="\n")
        print(f"froze {SNAPSHOT.relative_to(PROJECT_ROOT)}")
        return 0

    findings = classify(baseline_fingerprint(), current)
    if args.diff or findings:
        for finding in findings:
            detail = f" ({finding['detail']})" if finding.get("detail") else ""
            print(f"{finding['level']:<21} {finding['kind']:<28} {finding['subject']}{detail}")
    breaking = [f for f in findings if f["level"] == BREAKING]
    if args.check and breaking:
        print(f"\nERROR  {len(breaking)} breaking change(s) against the RC 1 contract snapshot")
        return 1
    if args.check:
        print("SDK 1 RC 1 contract snapshot: no breaking changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
