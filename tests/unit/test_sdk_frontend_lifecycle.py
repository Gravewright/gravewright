"""Phase 11 — frontend lifecycle and capability sync (static checks).

There is no JS test runner in this project, so per the plan we pin the browser
SDK runtime with static source assertions: the register() ownership/lifecycle
<<<<<<< HEAD
guards, setup/ready idempotency, listener-error isolation, debug gating, and the
=======
guards, setup/ready idempotency, hook-error isolation, debug gating, and the
>>>>>>> origin/main
capability map / status invariants against the canonical registry.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.sdk.capability_registry import get_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = (PROJECT_ROOT / "static" / "js" / "sdk" / "gravewright-sdk.js").read_text(encoding="utf-8")
STABILITY_POLICY = (PROJECT_ROOT / "docs" / "sdk" / "stability-policy.md").read_text(encoding="utf-8")


# --- register() guards -------------------------------------------------------


def test_frontend_register_requires_id():
    assert 'GravewrightSDK.register requires an id' in RUNTIME


def test_frontend_register_requires_package_script():
    assert 'outside a package script' in RUNTIME


def test_frontend_register_rejects_invalid_nonce():
    assert 'missing or invalid nonce' in RUNTIME


def test_frontend_register_rejects_id_mismatch():
    assert 'from script owned by' in RUNTIME


def test_frontend_register_rejects_inactive_package():
    assert 'inactive package' in RUNTIME


def test_frontend_register_rejects_duplicate_package():
    assert 'duplicate package' in RUNTIME


# --- lifecycle idempotency + isolation ---------------------------------------


def test_frontend_setup_runs_once():
    assert 'if (setupDone.has(id)) return;' in RUNTIME
    assert 'setupDone.add(id);' in RUNTIME


def test_frontend_ready_runs_once():
    assert 'if (readyDone.has(id)) return;' in RUNTIME
    assert 'readyDone.add(id);' in RUNTIME


<<<<<<< HEAD
def test_frontend_listener_error_isolated():
    # emit() wraps each listener call so one failing listener cannot break the rest.
    assert 'try {' in RUNTIME and 'listener' in RUNTIME.lower()
=======
def test_frontend_hook_error_isolated():
    # emit() wraps each listener call so one failing hook cannot break the rest.
    assert 'try {' in RUNTIME and 'hook' in RUNTIME.lower()
>>>>>>> origin/main
    assert 'console.error' in RUNTIME


def test_frontend_debug_api_gated_on_debug_flag():
    assert 'context.debug === true' in RUNTIME
    assert 'GravewrightSDKDebug' in RUNTIME


# --- capability map / status invariants --------------------------------------


def test_frontend_capability_map_matches_canonical_registry():
    import re

    source = (PROJECT_ROOT / "static" / "js" / "sdk" / "sdk-capabilities.js").read_text(
        encoding="utf-8"
    )
    name_to_value = dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", source))
    js_gates = {
        method: name_to_value[cap]
        for method, cap in re.findall(r"\"([^\"]+)\":\s*CAPABILITIES\.(\w+)", source)
    }
    registry = get_registry()
<<<<<<< HEAD
    all_gates = registry.method_to_capability()
    # No drift, and full coverage of every registry gate.
    for method, cap in js_gates.items():
        assert all_gates.get(method) == cap, method
    assert set(all_gates) <= set(js_gates)


def test_hooks_client_capability_is_removed():
    assert get_registry().status_of("hooks.client") is None
    assert "hooks.client" not in STABILITY_POLICY
=======
    all_gates = registry.method_to_capability(include_experimental=True)
    # No drift, and full coverage of the shipping (stable) gates.
    for method, cap in js_gates.items():
        assert all_gates.get(method) == cap, method
    assert set(registry.method_to_capability(include_experimental=False)) <= set(js_gates)


def test_hooks_client_documented_as_legacy_experimental():
    assert get_registry().status_of("hooks.client") == "legacy_experimental"
    assert "legacy_experimental" in STABILITY_POLICY
    assert "hooks.client" in STABILITY_POLICY
>>>>>>> origin/main


def test_frontend_storage_sqlite_requires_capability():
    # The runtime storage methods are gated on the storage.sqlite capability in
<<<<<<< HEAD
    # the canonical registry.
    gates = get_registry().method_to_capability()
=======
    # the canonical registry (frontend wiring lands with Phase 7B).
    gates = get_registry().method_to_capability(include_experimental=True)
>>>>>>> origin/main
    assert gates["storage.sqlite.query"] == "storage.sqlite"
    assert gates["storage.sqlite.execute"] == "storage.sqlite"
