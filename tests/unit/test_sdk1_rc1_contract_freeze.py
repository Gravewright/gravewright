"""SDK 1 RC 1 contract freeze.

The generated contract may be reformatted, reordered and reworded freely. What a
published package depends on may not change by accident, so the semantic
fingerprint is frozen and every difference against it is classified.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.sdk1_contract_snapshot import (
    BREAKING, COMPATIBLE, POTENTIALLY_BREAKING, SNAPSHOT,
    baseline_fingerprint, classify, current_fingerprint, fingerprint,
)


ROOT = Path(__file__).resolve().parents[2]


def _levels(findings, kind):
    return [f["level"] for f in findings if f["kind"] == kind]


# --- the freeze itself ---------------------------------------------------------

def test_the_current_contract_has_no_breaking_drift_from_the_rc1_snapshot():
    findings = classify(baseline_fingerprint(), current_fingerprint())
    breaking = [f for f in findings if f["level"] == BREAKING]
    assert breaking == [], breaking


def test_rc1_snapshot_records_the_certified_contract_shape():
    snapshot = baseline_fingerprint()
    assert snapshot["sdkVersion"] == "1"
    assert len(snapshot["methods"]) == 264
    assert len(snapshot["capabilities"]) == 116
    assert len(snapshot["events"]) == 51
    assert len(snapshot["errors"]) == 25
    # 291 since the RC 1 Input Registry correction added InputCommandInvocationDTO,
    # the semantic invocation a package handler receives instead of a browser event.
    assert len(snapshot["dtos"]) == 291
    # Every method resolves to a capability that exists in the same snapshot.
    assert all(m["capability"] in set(snapshot["capabilities"]) for m in snapshot["methods"].values())
    # Nothing in the frozen surface is an unresolved shape.
    assert all(m["returns"] not in {"", "any", "unknown", "JsonValue"} for m in snapshot["methods"].values())


def test_snapshot_tool_regenerates_byte_identical_output(tmp_path):
    """`--write` must be reproducible, so a re-freeze is a real diff or nothing."""
    before = SNAPSHOT.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/sdk1_contract_snapshot.py"), "--write"],
                   cwd=ROOT, check=True, capture_output=True)
    assert SNAPSHOT.read_text(encoding="utf-8") == before


def test_check_mode_passes_on_the_frozen_contract():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/sdk1_contract_snapshot.py"), "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# --- the classifier ------------------------------------------------------------

def _mutated(**changes):
    """Apply a mutation to a copy of the frozen baseline."""
    after = copy.deepcopy(baseline_fingerprint())
    changes["mutate"](after)
    return classify(baseline_fingerprint(), after)


def test_removing_a_method_is_breaking():
    findings = _mutated(mutate=lambda c: c["methods"].pop("scene.active"))
    assert _levels(findings, "method_removed") == [BREAKING]


def test_renaming_a_method_is_breaking_in_both_directions():
    def mutate(contract):
        contract["methods"]["scene.current"] = contract["methods"].pop("scene.active")
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "method_removed") == [BREAKING]
    # The replacement is still surfaced for review rather than silently accepted.
    assert _levels(findings, "method_added") == [POTENTIALLY_BREAKING]


def test_a_new_method_is_structurally_compatible_but_needs_rc_review():
    def mutate(contract):
        contract["methods"]["scene.teleport"] = {
            "capability": "scene.read", "returns": "SceneDTO", "required": [],
            "optional": [], "asynchronous": True}
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "method_added") == [POTENTIALLY_BREAKING]
    assert not [f for f in findings if f["level"] == BREAKING]


def test_making_an_optional_parameter_required_is_breaking():
    def mutate(contract):
        method = contract["methods"]["scene.zones.create"]
        moved = method["optional"].pop(0)
        method["required"] = method["required"] + [moved]
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "parameter_now_required") == [BREAKING]


def test_adding_an_optional_parameter_is_compatible():
    def mutate(contract):
        contract["methods"]["scene.active"]["optional"] = ["options"]
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "optional_parameter_added") == [COMPATIBLE]
    assert not [f for f in findings if f["level"] == BREAKING]


def test_removing_a_dto_field_is_breaking():
    def mutate(contract):
        contract["dtos"]["TokenDTO"]["fields"].pop("controllers")
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "dto_field_removed") == [BREAKING]


def test_narrowing_a_public_type_is_breaking():
    def mutate(contract):
        contract["dtos"]["TokenDTO"]["fields"]["name"] = "string"
    findings = _mutated(mutate=mutate)
    assert _levels(findings, "dto_field_type_changed") == [BREAKING]


def test_a_new_required_dto_field_is_breaking_but_an_optional_one_is_not():
    def required(contract):
        contract["dtos"]["TokenDTO"]["fields"]["mandatory"] = "string"
        contract["dtos"]["TokenDTO"]["required"].append("mandatory")

    def optional(contract):
        contract["dtos"]["TokenDTO"]["fields"]["extra"] = "string | null"

    assert _levels(_mutated(mutate=required), "dto_required_field_added") == [BREAKING]
    assert _levels(_mutated(mutate=optional), "dto_field_added") == [COMPATIBLE]


def test_changing_the_return_type_or_capability_of_a_method_is_breaking():
    def returns(contract):
        contract["methods"]["scene.active"]["returns"] = "string"

    def capability(contract):
        contract["methods"]["scene.active"]["capability"] = "scene.geometry.read"

    assert _levels(_mutated(mutate=returns), "method_return_changed") == [BREAKING]
    assert _levels(_mutated(mutate=capability), "method_capability_changed") == [BREAKING]


@pytest.mark.parametrize("collection,kind", [
    ("capabilities", "capability_removed"), ("events", "event_removed"), ("errors", "error_removed")])
def test_removing_a_capability_event_or_error_is_breaking(collection, kind):
    findings = _mutated(mutate=lambda c: c[collection].pop(0))
    assert _levels(findings, kind) == [BREAKING]


def test_changing_the_sdk_version_is_breaking():
    findings = _mutated(mutate=lambda c: c.__setitem__("sdkVersion", "2"))
    assert _levels(findings, "sdk_version_changed") == [BREAKING]


def test_reformatting_the_generated_contract_is_not_a_semantic_change():
    """Prose, ordering and formatting are explicitly outside the frozen surface."""
    contract = json.loads((ROOT / "docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
    reordered = copy.deepcopy(contract)
    reordered["methods"] = list(reversed(reordered["methods"]))
    for method in reordered["methods"]:
        method["lifecycle"] = "reworded lifecycle prose"
        method["errors"] = list(reversed(method["errors"]))
    assert classify(fingerprint(contract), fingerprint(reordered)) == []
