"""Package Doctor must recognise capabilities used through declared registries.

A registered action is executed by core from the manifest's action registry, so it
never appears as an `sdk.<method>(` call. Scanning only for call sites reported a
mandatory capability as unused; this is generic to any package that ships actions.
"""

from __future__ import annotations

import json

from tests.conftest import seed_campaign, seed_user


PACKAGE_ID = "declarative-addon"

ACTIONS = {"actions": [{
    "id": "state.mark", "version": 1,
    "inputs": {"type": "object", "properties": {"actorId": {"type": "string"}},
               "required": ["actorId"], "additionalProperties": False},
    "operations": [{"op": "actor.data.patch", "actorId": "$input.actorId",
                    "patch": {"declarative.marked": "YES"}}],
    "idempotency": "IDEMPOTENT",
}]}


def _manifest(capabilities, *, with_registry):
    manifest = {
        "schemaVersion": 1, "sdkVersion": "1", "kind": "addon", "id": PACKAGE_ID,
        "name": "Declarative Addon", "version": "1.0.0", "authors": ["Test"], "license": "MIT",
        "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": capabilities, "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {"game": {"scripts": ["main.js"]}},
        "provides": {"rules": {"actionRegistry": "rules/actions.gw.json"}} if with_registry else {},
    }
    return manifest


def _install(tmp_path, monkeypatch, gm, campaign, capabilities, *, with_registry=True):
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_activation_service import PackageActivationService
    from app.engine.sdk.package_install_service import PackageInstallService

    root = tmp_path / "packages"
    package = root / "addons" / PACKAGE_ID
    (package / "rules").mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps(_manifest(capabilities, with_registry=with_registry)), encoding="utf-8")
    (package / "rules" / "actions.gw.json").write_text(json.dumps(ACTIONS), encoding="utf-8")
    # Source that calls nothing: only the declared registry can justify a capability.
    (package / "main.js").write_text('window.GravewrightSDK.register({ id: "declarative-addon" });\n', encoding="utf-8")
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", root)
    assert PackageInstallService().install(package_id=PACKAGE_ID, user_id=gm).success
    assert PackageInstallService().enable(package_id=PACKAGE_ID).success
    assert PackageActivationService().activate_package(campaign, PACKAGE_ID, gm).success


def _warnings(package_id=PACKAGE_ID):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    return {f.details.get("capability") for f in PackageDoctorService().audit()
            if f.package_id == package_id and f.code == "capability_declared_unused"}


def test_capabilities_required_by_a_declared_action_registry_count_as_used(db, tmp_path, monkeypatch):
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install(tmp_path, monkeypatch, gm, campaign, ["actors.data.write", "rules.actions"])

    # Neither is called from source; both are mandatory for the declared action.
    assert _warnings() == set()


def test_a_capability_no_declaration_justifies_is_still_reported(db, tmp_path, monkeypatch):
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install(tmp_path, monkeypatch, gm, campaign,
             ["actors.data.write", "rules.actions", "scene.zones.read"])

    # The registry says nothing about zones, so that declaration stays flagged.
    assert _warnings() == {"scene.zones.read"}


def test_without_a_registry_the_same_declarations_are_reported_again(db, tmp_path, monkeypatch):
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install(tmp_path, monkeypatch, gm, campaign, ["actors.data.write", "rules.actions"],
             with_registry=False)

    assert _warnings() == {"actors.data.write", "rules.actions"}
