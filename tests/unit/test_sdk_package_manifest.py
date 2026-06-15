from __future__ import annotations

from app.engine.sdk.package_manifest import PackageKind, PackageManifest


def _addon() -> dict:
    return {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": "my-addon",
        "name": "My Addon",
        "version": "0.1.0",
        "authors": ["Alice", {"name": "Bob"}],
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["assets.scripts", "settings"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {"game": {"styles": ["assets/a.css"], "scripts": ["assets/a.js"]}},
        "settings": [{"key": "enabled", "scope": "user", "type": "boolean", "default": True}],
        "provides": {},
    }


def test_kind_values():
    assert PackageKind.values() == {"ruleset", "addon", "library", "content", "theme", "assets"}


def test_from_dict_parses_core_fields():
    m = PackageManifest.from_dict(_addon())
    assert m.kind == "addon"
    assert m.id == "my-addon"
    assert m.version == "0.1.0"
    assert m.capabilities == ["assets.scripts", "settings"]
    assert m.activation.mode == "multiple"
    assert m.author_names() == ["Alice", "Bob"]
    assert m.entrypoint_styles("game") == ["assets/a.css"]
    assert m.entrypoint_scripts("game") == ["assets/a.js"]
    assert m.settings[0].key == "enabled"


def test_referenced_paths_collects_entrypoints():
    m = PackageManifest.from_dict(_addon())
    assert set(m.referenced_paths()) == {"assets/a.css", "assets/a.js"}


def test_ruleset_domain_accessors():
    raw = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "ruleset",
        "id": "rs",
        "name": "RS",
        "version": "0.1.0",
        "compatibility": {"verified": "1.0.0-rc.1"},
        "capabilities": ["actors.register"],
        "activation": {"mode": "exclusive"},
        "entrypoints": {},
        "provides": {
            "storage": {"model": "scoped-json-v1"},
            "actorTypes": [{"id": "character", "label": "Character", "schema": "schemas/c.json"}],
            "rules": {"actions": "rules/actions.gw.json"},
            "locales": {"en": "locales/en.json"},
        },
    }
    m = PackageManifest.from_dict(raw)
    assert m.storage_model == "scoped-json-v1"
    assert [t.id for t in m.actor_types] == ["character"]
    assert m.rules["actions"] == "rules/actions.gw.json"
    assert m.locales["en"] == "locales/en.json"
    assert "schemas/c.json" in m.referenced_paths()


def test_summary_shape():
    s = PackageManifest.from_dict(_addon()).summary()
    assert s["id"] == "my-addon"
    assert s["kind"] == "addon"
    assert s["activation"] == {"scope": "campaign", "mode": "multiple"}
