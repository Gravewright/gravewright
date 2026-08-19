"""Black Vault as the permanent SDK 1 RC conformance / extreme stress package.

This certifies the package itself: its manifest is valid, Package Doctor accepts
it, it touches no private API, and its public-surface coverage is recorded so a
silent narrowing of what the stress package exercises is visible.
"""

from __future__ import annotations

import json
import re

from app.engine.sdk.capability_registry import get_registry
from tests.unit.test_black_vault_mission import PACKAGE_DIR, install, world


SCRIPT = (PACKAGE_DIR / "assets" / "black-vault.js").read_text(encoding="utf-8")
MANIFEST = json.loads((PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
REGISTRY = get_registry()

# The conformance package must stay reachable through the public contract alone.
PRIVATE_API = {
    "internal route": r"[\"'`]/(?:game|api|sdk/internal)/",
    "raw websocket": r"\bnew\s+WebSocket\b",
    "renderer": r"\bPIXI\b|\bGravewrightMap\b|\bGravewrightRenderer\b",
    "host dom": r"\bdocument\s*\.\s*(?:querySelector|getElementById|body|head|cookie)\b",
    "raw transport": r"\bfetch\s*\(|\bXMLHttpRequest\b|\bEventSource\b",
    "storage escape": r"\blocalStorage\b|\bindexedDB\b|\brequire\s*\(|\bimport\s*\(",
    "filesystem": r"\bfs\s*\.\s*read|[A-Za-z]:[\/]{1,2}|\bprocess\s*\.\s*env\b",
    "server internals": r"\bapp\.engine\b|\bapp\.persistence\b|Repository\(|Service\(\)",
    "sql": r"\b(?:SELECT|INSERT|UPDATE|DELETE)\s+(?:\*|FROM|INTO|SET)\b",
}


def _used_methods() -> list[str]:
    methods = REGISTRY.method_to_capability()
    return sorted(
        method for method in methods
        if re.search(rf"\bsdk\s*\.\s*{re.escape(method).replace(chr(92) + '.', chr(92) + 's*' + chr(92) + '.' + chr(92) + 's*')}\s*\(", SCRIPT)
    )


def test_black_vault_uses_zero_private_api():
    offenders = {label: re.findall(pattern, SCRIPT) for label, pattern in PRIVATE_API.items()}
    assert {label: hits for label, hits in offenders.items() if hits} == {}


def test_black_vault_manifest_is_a_valid_sdk_1_addon():
    from app.engine.sdk.package_manifest_validator import validate_manifest

    result = validate_manifest(MANIFEST)
    assert result.ok, result.errors
    assert MANIFEST["sdkVersion"] == "1"
    assert MANIFEST["kind"] == "addon"
    # Every declared capability is a real, non-forbidden registry entry.
    for capability in MANIFEST["capabilities"]:
        assert REGISTRY.status_of(capability) is not None, capability
        assert capability not in REGISTRY.forbidden_names(), capability


def test_black_vault_declares_every_capability_its_calls_require():
    declared = set(MANIFEST["capabilities"])
    methods = REGISTRY.method_to_capability()
    undeclared = {methods[m] for m in _used_methods()} - declared
    assert undeclared == set()


def test_black_vault_public_surface_coverage_is_recorded():
    """A drop in coverage means the stress package stopped stressing something."""
    used = _used_methods()
    methods = REGISTRY.method_to_capability()
    events = sorted(set(re.findall(r'sdk\.events\.on\("([^"]+)"', SCRIPT)))
    domains = sorted({method.split(".")[0] for method in used})

    assert len(used) >= 51, len(used)
    assert len(MANIFEST["capabilities"]) >= 45
    assert len({methods[m] for m in used}) >= 38
    assert events == ["scene.object.interacted", "zone.entered"]
    assert set(domains) >= {
        "actors", "campaign", "cards", "content", "events", "gameplay", "input", "journals",
        "navigation", "scene", "settings", "sounds", "storage", "timelines", "tokens", "ui",
        "workflows",
    }


def test_black_vault_passes_package_doctor_with_no_errors(db, tmp_path, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    gm, _a, _b, campaign = world()
    install(tmp_path, monkeypatch, gm, campaign)
    findings = [f for f in PackageDoctorService().audit() if f.package_id == "black-vault"]

    assert [f for f in findings if f.severity == "error"] == []
    for code in ("capability_unknown", "capability_forbidden", "capability_used_undeclared",
                 "package_internal_route_access"):
        assert [f for f in findings if f.code == code] == [], code

    # Remaining warnings are the documented Doctor limitation, not invalid declarations.
    unused = {f.details.get("capability") for f in findings if f.code == "capability_declared_unused"}
    assert unused <= {"audio.playback", "interactions.request", "interactions.respond"}
