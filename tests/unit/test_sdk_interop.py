"""``sdk.bus.*`` interop — stable, frozen by Alpha 2.0.0 SDK Freeze.

Validates the manifest ``interop`` block (namespacing, event names, schema
paths), the on-disk schema existence check, the doctor surfacing, and — via
static source checks, since there is no JS runner — that the frontend bus is the
package-to-package channel. The strict enforcement policy requires a package to
declare every event/method it publishes, subscribes, provides, or requests.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from app.engine.sdk.capability_registry import get_registry
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_interop import validate_interop_manifest
from app.engine.sdk.package_loader import load_package

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = (PROJECT_ROOT / "static" / "js" / "sdk" / "gravewright-sdk.js").read_text(encoding="utf-8")


def _manifest(interop: dict, *, package_id: str = "my-addon") -> dict:
    return {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": package_id,
        "name": "My Addon",
        "version": "1.0.0",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["bus.publish", "bus.subscribe"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
        "interop": interop,
    }


# --- manifest validation -----------------------------------------------------


def test_interop_valid_block_validates_clean():
    raw = _manifest(
        {
            "emits": {"my-addon.inventory.changed": {"schema": "schemas/inv.json"}},
            "listens": {"gravewright.actor.updated": {"optional": True}},
        }
    )
    assert validate_interop_manifest(raw) == []


def test_interop_namespace_forbidden_for_foreign_emit():
    raw = _manifest({"emits": {"other-addon.changed": {}}})
    assert "sdk.interop.namespace_forbidden" in validate_interop_manifest(raw)


def test_interop_namespace_forbidden_for_reserved_emit():
    raw = _manifest({"emits": {"gravewright.actor.updated": {}}})
    assert "sdk.interop.namespace_forbidden" in validate_interop_manifest(raw)


def test_interop_namespace_forbidden_for_system_emit():
    raw = _manifest({"emits": {"system.actor.updated": {}}})
    assert "sdk.interop.namespace_forbidden" in validate_interop_manifest(raw)


def test_interop_event_name_invalid():
    raw = _manifest({"emits": {"NotADottedName": {}}})
    assert "sdk.interop.event_name_invalid" in validate_interop_manifest(raw)


def test_interop_listens_allows_core_namespace():
    raw = _manifest({"listens": {"gravewright.actor.updated": {}}})
    # Listening to a core event is allowed; only emitting/providing is namespaced.
    assert "sdk.interop.namespace_forbidden" not in validate_interop_manifest(raw)


def test_interop_event_schema_path_validated():
    raw = _manifest({"emits": {"my-addon.changed": {"schema": "../escape.json"}}})
    assert "sdk.interop.schema_path_unsafe" in validate_interop_manifest(raw)


def test_interop_rpc_params_returns_paths_validated():
    raw = _manifest(
        {
            "provides": {
                "my-addon.state.get": {
                    "params": "schemas/rpc/get.request.json",
                    "returns": "../escape.json",
                }
            }
        }
    )
    assert "sdk.interop.schema_path_unsafe" in validate_interop_manifest(raw)


def test_interop_provides_requires_own_namespace():
    raw = _manifest({"provides": {"other.getWeight": {}}})
    assert "sdk.interop.namespace_forbidden" in validate_interop_manifest(raw)


# --- disk + doctor -----------------------------------------------------------


def test_interop_doctor_reports_missing_schema(tmp_path):
    pkg = tmp_path / "my-addon"
    pkg.mkdir()
    raw = _manifest({"emits": {"my-addon.changed": {"schema": "schemas/missing.json"}}})
    (pkg / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")

    loaded = load_package(pkg, expected_id="my-addon", expected_kind_root="addons")
    assert "sdk.interop.schema_missing" in loaded.validation.errors


def test_interop_valid_schema_on_disk_loads_clean(tmp_path):
    pkg = tmp_path / "my-addon"
    (pkg / "schemas").mkdir(parents=True)
    (pkg / "schemas" / "inv.json").write_text("{}", encoding="utf-8")
    raw = _manifest({"emits": {"my-addon.inventory.changed": {"schema": "schemas/inv.json"}}})
    (pkg / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")

    loaded = load_package(pkg, expected_id="my-addon", expected_kind_root="addons")
    interop_errors = [c for c in loaded.validation.errors if c.startswith("sdk.interop.")]
    assert interop_errors == []


def test_doctor_reports_provider_conflict(monkeypatch):
    doctor = PackageDoctorService()

    def manifest(package_id):
        return SimpleNamespace(
            raw={"interop": {"provides": {"shared.method": {"params": "p", "returns": "r"}}}}
        )

    monkeypatch.setattr(doctor.install, "get_manifest", manifest)
    findings = doctor._audit_campaign_interop("camp", {"pkg-a", "pkg-b"})
    assert {f.code for f in findings} == {"bus.provider_conflict"}


def test_doctor_reports_required_provider_missing(monkeypatch):
    doctor = PackageDoctorService()

    def manifest(package_id):
        if package_id == "consumer":
            return SimpleNamespace(
                raw={"interop": {"requires": {"provider.method": {"optional": False}}}}
            )
        return SimpleNamespace(raw={"interop": {}})

    monkeypatch.setattr(doctor.install, "get_manifest", manifest)
    findings = doctor._audit_campaign_interop("camp", {"consumer", "other"})
    assert [f.code for f in findings] == ["bus.provider_not_found"]


# --- capabilities ------------------------------------------------------------


def test_bus_capabilities_are_stable():
    registry = get_registry()
    for name in ("bus.publish", "bus.subscribe", "bus.request", "bus.provide"):
        assert registry.status_of(name) == "stable", name


# --- frontend: bus is clean and separate from hooks --------------------------


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    depth = 0
    i = source.index("{", start)
    for j in range(i, len(source)):
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
            if depth == 0:
                return source[i : j + 1]
    return source[i:]


def test_bus_publish_requires_capability():
    assert 'requireCap("bus.publish")' in RUNTIME
    assert 'requireCap("bus.subscribe")' in RUNTIME


def test_bus_publish_rejects_foreign_namespace():
    assert "cannot publish to foreign namespace" in RUNTIME


def test_bus_publish_requires_manifest_declaration():
    assert "sdk.interop.event_undeclared" in RUNTIME
    assert 'interopDeclares(pkg, "emits", event)' in RUNTIME


def test_bus_subscribe_requires_manifest_declaration():
    # Strict policy (Alpha 2.0.0): subscribe requires interop.listens.
    body = _function_body(RUNTIME, "buildScopedSdk")
    assert 'interopDeclares(pkg, "listens", event)' in body
    assert "did not declare listened event" in body


def test_bus_request_requires_manifest_declaration():
    # Strict policy (Alpha 2.0.0): request requires interop.requires.
    body = _function_body(RUNTIME, "buildScopedSdk")
    assert 'interopDeclares(pkg, "requires", name)' in body
    assert "did not declare required method" in body


def test_bus_has_dedicated_listener_map():
    assert "const busListeners = new Map();" in RUNTIME


def test_legacy_hook_bus_is_removed():
    # The legacy sdk.hooks/sdk.events client hook bus is gone entirely.
    assert "const listeners = new Map();" not in RUNTIME
    assert "sdk.hooks" not in RUNTIME
    assert 'requireCap("hooks.on")' not in RUNTIME
    assert 'requireCap("events.on")' not in RUNTIME


# --- frontend: request/provide RPC -------------------------------------------


def test_bus_provide_requires_capability():
    assert 'requireCap("bus.provide")' in RUNTIME


def test_bus_request_requires_capability():
    assert 'requireCap("bus.request")' in RUNTIME


def test_bus_provide_rejects_foreign_namespace():
    assert "cannot provide in foreign namespace" in RUNTIME


def test_bus_provide_requires_manifest_declaration():
    assert "sdk.interop.method_undeclared" in RUNTIME
    assert 'interopDeclares(pkg, "provides", name)' in RUNTIME


def test_bus_request_missing_provider_returns_structured_error():
    body = _function_body(RUNTIME, "busRequest")
    assert "bus.provider_not_found" in body


def test_bus_provider_timeout_returns_structured_error():
    body = _function_body(RUNTIME, "busRequest")
    assert "bus.provider_timeout" in body
    assert "timeoutMs" in body
    assert "setTimeout" in body and "Promise.race" in body


def test_bus_duplicate_provider_policy_enforced():
    body = _function_body(RUNTIME, "busProvide")
    assert "busProviders.has(key)" in body
    assert "duplicate provider" in body
    assert "bus.provider_conflict" in body
    assert "busProviders.delete(key)" in body


def test_bus_provider_receives_caller_context():
    body = _function_body(RUNTIME, "busRequest")
    assert "providerContext" in body
    assert "callerPackageId" in body
    assert "providerPackageId" in body
    assert "provider.handler(frozen, providerContext)" in body


def test_bus_request_returns_structured_result_shape():
    body = _function_body(RUNTIME, "busRequest")
    # BusResult: { ok: true, value } | { ok: false, error: { code, message } }.
    assert "ok: true" in body
    assert "Object.prototype.hasOwnProperty.call(value, \"value\")" in body
    assert "busError(" in RUNTIME


def test_bus_rpc_capabilities_are_stable():
    registry = get_registry()
    assert registry.status_of("bus.request") == "stable"
    assert registry.status_of("bus.provide") == "stable"
