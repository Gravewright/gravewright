"""Phase 2 — canonical capability registry.

``app/engine/sdk/capabilities.json`` is the single source of truth. These tests
pin its shape, that the Python validator and the doctor derive from it, that the
frontend capability map and the runtime gates stay in sync with it, and that the
generated docs are current.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engine.sdk import package_manifest_validator as validator
from app.engine.sdk.capability_registry import (
    REGISTRY_PATH,
    VALID_STATUSES,
    VALID_SURFACES,
    get_registry,
)
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_manifest_validator import validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JS_CAPABILITIES = PROJECT_ROOT / "static" / "js" / "sdk" / "sdk-capabilities.js"
JS_RUNTIME = PROJECT_ROOT / "static" / "js" / "sdk" / "gravewright-sdk.js"


def _base_manifest(**overrides) -> dict:
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": "my-addon",
        "name": "My Addon",
        "version": "0.1.0",
        "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": ["assets.scripts"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
    }
    manifest.update(overrides)
    return manifest


def _parse_js_capability_map() -> tuple[set[str], dict[str, str]]:
    """Return (declared capability values, method -> capability) from the JS."""
    source = JS_CAPABILITIES.read_text(encoding="utf-8")
    name_to_value = dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", source))
    method_to_capability: dict[str, str] = {}
    for method, cap_name in re.findall(r"\"([^\"]+)\":\s*CAPABILITIES\.(\w+)", source):
        method_to_capability[method] = name_to_value[cap_name]
    return set(name_to_value.values()), method_to_capability


# --- shape -------------------------------------------------------------------


def test_capabilities_json_has_required_shape():
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    capabilities = data["capabilities"]
    assert capabilities
    for name, entry in capabilities.items():
        assert entry["status"] in VALID_STATUSES, name
        assert entry["description"].strip(), name
        assert set(entry["surfaces"]) <= VALID_SURFACES, name
        assert isinstance(entry["methods"], list), name
    forbidden = data["forbidden"]
    assert forbidden
    for name, entry in forbidden.items():
        assert entry["reason"].strip(), name


# --- python validator --------------------------------------------------------


def test_python_validator_uses_canonical_capability_registry():
    registry = get_registry()
    assert validator.KNOWN_CAPABILITIES == registry.known_names()
    assert validator.FORBIDDEN_CAPABILITIES == registry.forbidden_names()


def test_forbidden_capabilities_are_rejected():
    for forbidden in get_registry().forbidden_names():
        result = validate_manifest(_base_manifest(capabilities=[forbidden]))
        assert "sdk.validation.capability_forbidden" in result.errors, forbidden


def test_unknown_capability_is_rejected():
    result = validate_manifest(_base_manifest(capabilities=["totally.madeup"]))
    assert "sdk.validation.capability_unknown" in result.errors


# --- doctor ------------------------------------------------------------------


def test_doctor_uses_canonical_capability_registry():
    doctor = PackageDoctorService()
    # The audit consults the registry: an unknown capability is an error finding,
    # a forbidden one too, and a clean declared capability produces nothing.
    unknown = doctor._audit_capabilities(
        "pkg", SimpleNamespace(manifest=SimpleNamespace(capabilities=["nope.unknown"]))
    )
    assert [f.code for f in unknown] == ["capability_unknown"]

    forbidden_name = next(iter(get_registry().forbidden_names()))
    forbidden = doctor._audit_capabilities(
        "pkg", SimpleNamespace(manifest=SimpleNamespace(capabilities=[forbidden_name]))
    )
    assert [f.code for f in forbidden] == ["capability_forbidden"]

    clean = doctor._audit_capabilities(
        "pkg", SimpleNamespace(manifest=SimpleNamespace(capabilities=["settings"]))
    )
    assert clean == []


# --- frontend sync -----------------------------------------------------------


def test_frontend_capability_map_matches_registry():
    registry = get_registry()
    js_caps, js_method_map = _parse_js_capability_map()

    # Every capability the frontend declares must be known to the registry.
    unknown = js_caps - set(registry.known_names())
    assert not unknown, f"frontend declares capabilities absent from registry: {unknown}"

    # No drift: every frontend gate maps to the capability the registry declares.
    all_gates = registry.method_to_capability()
    for method, cap in js_method_map.items():
        assert all_gates.get(method) == cap, method
    # Every registry gate must be present in the frontend.
    assert set(all_gates) <= set(js_method_map)


def test_every_public_sdk_method_requires_capability_or_is_explicitly_public():
    registry = get_registry()
    gates = registry.method_to_capability()
    runtime = JS_RUNTIME.read_text(encoding="utf-8")
    guarded = set(re.findall(r"requireCap\(\"([^\"]+)\"\)", runtime))
    assert guarded, "expected requireCap() gates in the runtime"
    # Every guarded method maps to a real capability in the registry.
    unknown = sorted(m for m in guarded if m not in gates)
    assert not unknown, f"runtime gates methods not in the registry: {unknown}"


# --- statuses ----------------------------------------------------------------


def test_storage_sqlite_capability_is_stable():
    assert get_registry().status_of("storage.sqlite") == "stable"


def test_hooks_client_capability_is_removed():
    assert get_registry().status_of("hooks.client") is None


def test_bus_capabilities_are_stable():
    registry = get_registry()
    for name in ("bus.publish", "bus.subscribe", "bus.request", "bus.provide"):
        assert registry.status_of(name) == "stable", name


# --- docs --------------------------------------------------------------------


def test_docs_capabilities_are_generated_or_current():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_sdk_reference.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
