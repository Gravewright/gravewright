from __future__ import annotations

from app.engine.sdk.package_manifest_validator import validate_manifest


def _base(**overrides) -> dict:
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": "my-addon",
        "name": "My Addon",
        "version": "0.1.0",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["assets.scripts"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
    }
    manifest.update(overrides)
    return manifest


def test_valid_addon_is_ok():
    result = validate_manifest(_base())
    assert result.ok
    assert result.compatibility_status == "compatible"


def test_not_object_rejected():
    assert not validate_manifest(["nope"]).ok


def test_bad_schema_and_sdk_version():
    r = validate_manifest(_base(schemaVersion=2, sdkVersion="2"))
    assert "sdk.validation.schema_version" in r.errors
    assert "sdk.validation.sdk_version" in r.errors


def test_invalid_id_and_kind():
    r = validate_manifest(_base(id="Bad_Id", kind="weird"))
    assert "sdk.validation.id_invalid" in r.errors
    assert "sdk.validation.kind" in r.errors


def test_forbidden_and_unknown_capabilities():
    r = validate_manifest(_base(capabilities=["backend.execute", "made.up"]))
    assert "sdk.validation.capability_forbidden" in r.errors
    assert "sdk.validation.capability_unknown" in r.errors


def test_addon_activation_mode_must_be_multiple():
    r = validate_manifest(_base(activation={"mode": "exclusive"}))
    assert "sdk.validation.addon_activation_mode" in r.errors


def test_ruleset_requires_storage_and_actor_types():
    r = validate_manifest(
        _base(kind="ruleset", activation={"mode": "exclusive"}, capabilities=["actors.register"], provides={})
    )
    assert "sdk.validation.ruleset_storage_required" in r.errors
    assert "sdk.validation.ruleset_actor_types_required" in r.errors


def test_ruleset_valid():
    r = validate_manifest(
        _base(
            kind="ruleset",
            activation={"mode": "exclusive"},
            capabilities=["actors.register"],
            provides={
                "storage": {"model": "scoped-json-v1"},
                "actorTypes": [{"id": "character", "label": "Character"}],
            },
        )
    )
    assert r.ok


def test_assets_must_not_declare_actor_types():
    r = validate_manifest(
        _base(
            kind="assets",
            capabilities=["assets.pack"],
            provides={"actorTypes": [{"id": "x", "label": "X"}]},
        )
    )
    assert "sdk.validation.assets_invalid_assets" in r.errors


def test_unsafe_path_rejected():
    r = validate_manifest(_base(entrypoints={"game": {"scripts": ["../escape.js"]}}))
    assert "sdk.validation.path_unsafe" in r.errors
