from __future__ import annotations

import pytest

from app.cli.scaffold import Intent, build_manifest, derive_capabilities
from app.engine.sdk.package_manifest_validator import validate_manifest


def test_ruleset_intent_derives_capabilities():
    intent = Intent(
        has_characters=True,
        has_monsters=True,
        has_items=True,
        has_sheets=True,
        has_rolls=True,
        has_combat=True,
        wants_content=True,
    )
    caps = derive_capabilities("ruleset", intent)
    assert "actors.register" in caps  # implied by actor types
    assert "items.register" in caps
    assert "sheets.declarative" in caps
    assert {"dice.roll", "rolls.intent"} <= set(caps)
    assert "combat.config" in caps
    assert "content.packs" in caps


def test_js_intent_adds_asset_capabilities():
    caps = derive_capabilities("addon", Intent(uses_js=True))
    assert {"assets.ui", "assets.styles", "assets.scripts"} <= set(caps)


def test_bare_addon_gets_a_default_capability():
    # Every package needs >= 1 capability; a side-effect-free default is used.
    assert derive_capabilities("addon", Intent(has_characters=False)) == ["settings"]


@pytest.mark.parametrize("kind", ["ruleset", "addon", "library", "theme", "assets", "content"])
def test_built_manifest_validates_for_every_kind(kind):
    intent = Intent(has_items=True, has_sheets=True, uses_js=(kind != "ruleset"))
    manifest = build_manifest(
        package_id="my-pack", name="My Pack", version="0.1.0", kind=kind, intent=intent
    )
    result = validate_manifest(manifest)
    assert result.ok, result.errors


def test_ruleset_manifest_has_storage_and_actor_types():
    manifest = build_manifest(
        package_id="my-rpg",
        name="My RPG",
        version="0.1.0",
        kind="ruleset",
        intent=Intent(has_characters=True, has_monsters=True, has_items=True),
    )
    assert manifest["provides"]["storage"]["model"] == "scoped-json-v1"
    actor_ids = {a["id"] for a in manifest["provides"]["actorTypes"]}
    assert actor_ids == {"character", "monster"}
    assert manifest["provides"]["itemTypes"]


def test_js_manifest_declares_entrypoints():
    manifest = build_manifest(
        package_id="fx", name="FX", version="0.1.0", kind="addon", intent=Intent(uses_js=True)
    )
    assert manifest["entrypoints"]["game"]["scripts"] == ["assets/main.js"]
