from __future__ import annotations

import json

import pytest

from app.cli.scaffold import (
    Intent,
    build_manifest,
    build_package,
    declared_sheet_type_ids,
    derive_capabilities,
    mechanic_ids,
)
from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.engine.rules.formula_engine import evaluate
from app.engine.sheets.sheet_validation import apply_schema_defaults


def _write(tmp_path, pkg):
    root = tmp_path / "rulesets" / pkg.manifest["id"]
    for rel, content in pkg.files.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return root


def _ruleset(package_id="my-rpg", name="My RPG", **intent_kwargs):
    intent_kwargs.setdefault("html_sheets", True)
    intent = Intent(has_sheets=True, **intent_kwargs)
    return build_package(package_id=package_id, name=name, kind="ruleset", intent=intent)


# --- capabilities -----------------------------------------------------------


def test_ruleset_with_sheets_derives_html_capabilities():
    caps = derive_capabilities(
        "ruleset",
        Intent(
            has_sheets=True,
            html_sheets=True,
            actor_types=("character",),
            item_types=("weapon",),
        ),
    )
    assert "actors.register" in caps
    assert "items.register" in caps
    assert {"sheets.html", "assets.styles", "sheets.richText"} <= set(caps)
    assert "sheets.declarative" not in caps
    assert "sheets.controller" not in caps


def test_rich_text_capability_follows_block_editors():
    # Item descriptions use the block editor -> richText.
    with_items = derive_capabilities(
        "ruleset", Intent(has_sheets=True, html_sheets=True, actor_types=("character",), item_types=("weapon",))
    )
    assert "sheets.richText" in with_items
    # Actor biography/notes tabs also use the block editor -> richText.
    with_bio = derive_capabilities(
        "ruleset", Intent(has_sheets=True, html_sheets=True, actor_types=("character",), wants_biography=True)
    )
    assert "sheets.richText" in with_bio
    # Plain actor-only ruleset (no editors) -> html but no richText.
    plain = derive_capabilities(
        "ruleset", Intent(has_sheets=True, html_sheets=True, actor_types=("character",))
    )
    assert "sheets.html" in plain
    assert "sheets.richText" not in plain
    # No sheets at all -> no html/richText.
    none = derive_capabilities("ruleset", Intent(has_sheets=False, actor_types=("character",)))
    assert "sheets.html" not in none


def test_biography_and_notes_render_as_tabs_with_block_editors():
    pkg = _ruleset(
        actor_types=("character",), mechanic="d20-attribute-modifier",
        wants_biography=True, wants_notes=True,
    )
    sheet = pkg.files["sheets/character.html"]
    # Real, root-scoped tabs (Main / Biography / Notes).
    assert 'data-tab="main"' in sheet
    assert 'data-tab="biography"' in sheet and 'data-tab-panel="biography"' in sheet
    assert 'data-tab="notes"' in sheet and 'data-tab-panel="notes"' in sheet
    # Biography/Notes are Notion-style block editors, not plain textareas.
    assert 'data-rich-editor="system.biography"' in sheet
    assert 'data-rich-editor="system.notes"' in sheet
    schema = json.loads(pkg.files["schemas/actors/character.schema.json"])
    assert schema["properties"]["biography"]["type"] == "object"
    assert schema["properties"]["notes"]["type"] == "object"


def test_actor_gets_items_list_when_ruleset_has_items():
    pkg = _ruleset(actor_types=("character", "npc"), item_types=("weapon",), mechanic="none")
    for actor_id in ("character", "npc"):
        sheet = pkg.files[f"sheets/{actor_id}.html"]
        assert 'data-item-list="system.items"' in sheet
        assert 'data-drop-zone="items"' in sheet
        schema = json.loads(pkg.files[f"schemas/actors/{actor_id}.schema.json"])
        assert schema["properties"]["items"]["type"] == "array"


def test_items_become_a_tab_alongside_other_panels():
    # With a mechanic (Main) plus Items there are >=2 panels -> real tabs.
    pkg = _ruleset(actor_types=("character",), item_types=("weapon",), mechanic="d20-attribute-modifier")
    sheet = pkg.files["sheets/character.html"]
    assert 'data-tab="main"' in sheet and 'data-tab="items"' in sheet
    assert 'data-tab-panel="items"' in sheet


def test_no_items_tab_without_item_types():
    pkg = _ruleset(actor_types=("character",), mechanic="d20-attribute-modifier")
    sheet = pkg.files["sheets/character.html"]
    assert "data-item-list" not in sheet


def test_item_description_uses_block_editor():
    pkg = _ruleset(actor_types=("character",), item_types=("weapon",))
    item = pkg.files["sheets/weapon.html"]
    assert 'data-rich-editor="system.description"' in item
    schema = json.loads(pkg.files["schemas/items/weapon.schema.json"])
    assert schema["properties"]["description"]["type"] == "object"


def test_tabs_disabled_by_default():
    pkg = _ruleset(actor_types=("character",), mechanic="none")
    sheet = pkg.files["sheets/character.html"]
    assert "data-tab=" not in sheet
    assert "data-rich-editor" not in sheet


def test_js_intent_adds_asset_capabilities():
    caps = derive_capabilities("addon", Intent(uses_js=True))
    assert {"assets.ui", "assets.styles", "assets.scripts"} <= set(caps)


def test_bare_addon_gets_a_default_capability():
    assert derive_capabilities("addon", Intent(has_characters=False)) == ["settings"]


# --- manifest structure -----------------------------------------------------


@pytest.mark.parametrize("kind", ["ruleset", "addon", "library", "theme", "assets", "content"])
def test_built_manifest_validates_for_every_kind(kind):
    intent = Intent(has_items=True, has_sheets=True, uses_js=(kind != "ruleset"))
    manifest = build_manifest(
        package_id="my-pack", name="My Pack", version="0.1.0", kind=kind, intent=intent
    )
    assert validate_manifest(manifest).ok


def test_default_html_scaffold(tmp_path):
    # Default ruleset (just --sheets) -> a character HTML sheet, shared CSS.
    pkg = _ruleset(package_id="demo")
    assert "sheets/character.html" in pkg.files
    assert "styles/sheet.css" in pkg.files
    assert not any(p.endswith("-sheet.css") for p in pkg.files)  # one shared stylesheet
    assert not any(p.startswith("layouts/") for p in pkg.files)  # no declarative IR
    assert not any(p.startswith("scripts/") for p in pkg.files)  # no controller
    sheet = pkg.manifest["provides"]["actorTypes"][0]["sheet"]
    assert sheet == {
        "mode": "html",
        "template": "sheets/character.html",
        "style": "styles/sheet.css",
    }
    assert pkg.manifest["entrypoints"]["game"]["styles"] == ["styles/sheet.css"]
    loaded = load_package(_write(tmp_path, pkg), expected_id="demo", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


def test_default_declarative_scaffold_is_simple_and_valid(tmp_path):
    pkg = _ruleset(
        package_id="simple",
        html_sheets=False,
        actor_types=("character",),
        mechanic="d20-attribute-modifier",
    )
    sheet_path = "layouts/character.sheet.gw.json"
    assert pkg.manifest["provides"]["actorTypes"][0]["sheet"] == sheet_path
    assert "sheets.declarative" in pkg.manifest["capabilities"]
    assert "sheets.html" not in pkg.manifest["capabilities"]
    assert sheet_path in pkg.files
    assert "styles/sheet.css" not in pkg.files
    layout = json.loads(pkg.files[sheet_path])
    assert layout["body"]["type"] == "section"
    assert any(node["type"] == "rollButton" for node in layout["body"]["children"])
    loaded = load_package(_write(tmp_path, pkg), expected_id="simple", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


def test_declarative_items_have_real_drop_zone_and_action(tmp_path):
    pkg = _ruleset(
        package_id="json-items",
        html_sheets=False,
        actor_types=("character",),
        item_types=("weapon",),
    )
    layout = json.loads(pkg.files["layouts/character.sheet.gw.json"])
    item_list = next(node for node in layout["body"]["children"] if node["type"] == "itemList")
    assert item_list["dropZone"] == {
        "type": "dropZone",
        "id": "items",
        "accepts": ["item"],
        "onDrop": "add-item",
    }
    actions = json.loads(pkg.files["rules/actions.gw.json"])["actions"]
    assert actions["add-item"] == {
        "type": "append",
        "target": "items",
        "value": "@drop.entry",
    }
    loaded = load_package(
        _write(tmp_path, pkg), expected_id="json-items", expected_kind_root="rulesets"
    )
    assert loaded.ok, loaded.validation.errors


@pytest.mark.parametrize("html_sheets", [False, True])
def test_effects_generate_type_schema_sheet_actor_area_and_drop_action(tmp_path, html_sheets):
    pkg = _ruleset(
        package_id="effects-rpg",
        html_sheets=html_sheets,
        actor_types=("character",),
        item_types=("weapon",),
        wants_effects=True,
    )
    assert [item["id"] for item in pkg.manifest["provides"]["itemTypes"]] == [
        "weapon",
        "effect",
    ]
    effect_schema = json.loads(pkg.files["schemas/items/effect.schema.json"])
    assert effect_schema["properties"]["modifiers"]["default"][0]["target"] == "roll.any"
    actor_schema = json.loads(pkg.files["schemas/actors/character.schema.json"])
    assert actor_schema["properties"]["effects"] == {"type": "array", "default": []}
    actions = json.loads(pkg.files["rules/actions.gw.json"])["actions"]
    assert actions["add-effect"]["target"] == "effects"
    if html_sheets:
        assert 'data-item-list="system.effects"' in pkg.files["sheets/character.html"]
        assert 'data-drop-zone="effects"' in pkg.files["sheets/character.html"]
        assert 'data-bind="system.modifiers.0.target"' in pkg.files["sheets/effect.html"]
    else:
        layout = json.loads(pkg.files["layouts/character.sheet.gw.json"])
        effects = next(
            node for node in layout["body"]["children"] if node.get("path") == "sheet.effects"
        )
        assert effects["row"] == {"type": "effectRow"}
        assert effects["dropZone"]["onDrop"] == "add-effect"
    loaded = load_package(
        _write(tmp_path, pkg), expected_id="effects-rpg", expected_kind_root="rulesets"
    )
    assert loaded.ok, loaded.validation.errors


@pytest.mark.parametrize(
    ("item_type", "expected_path"),
    [("weapon", "damage"), ("armor", "armor"), ("spell", "level"), ("potion", "quantity")],
)
def test_item_family_gets_symbolic_starter_fields(item_type, expected_path):
    pkg = _ruleset(actor_types=("character",), item_types=(item_type,))
    schema = json.loads(pkg.files[f"schemas/items/{item_type}.schema.json"])
    assert expected_path in schema["properties"]
    assert "category" in schema["properties"]
    assert f'data-bind="system.{expected_path}"' in pkg.files[f"sheets/{item_type}.html"]


def test_mechanic_writes_executable_roll_action():
    pkg = _ruleset(actor_types=("character",), mechanic="2d6-pbta")
    actions = json.loads(pkg.files["rules/actions.gw.json"])["actions"]
    assert actions["move-roll"] == {
        "type": "roll",
        "label": "Roll move",
        "formula": "2d6 + @sheet.stats.cool",
    }


def test_exploding_mechanic_uses_sheet_parameters():
    pkg = _ruleset(actor_types=("character",), mechanic="exploding-dice")
    action = json.loads(pkg.files["rules/actions.gw.json"])["actions"]["exploding-roll"]
    assert action["formula"] == "explode(@sheet.die.size, @sheet.die.explode)"


@pytest.mark.parametrize(
    ("mechanic", "formula"),
    [
        ("d20-attribute-modifier-skill", "1d20 + floor((@sheet.attributes.strength - 10) / 2) + @sheet.skills.athletics"),
        ("d20-attribute-modifier", "1d20 + floor((@sheet.attributes.strength - 10) / 2)"),
        ("d20-roll-under", "under(1, 20, clamp(@sheet.attributes.strength, 1, 20))"),
        ("d100-percentile", "under(1, 100, clamp(@sheet.skills.perception, 1, 100))"),
        ("dice-pool-successes", "successes(clamp(@sheet.pool.size, 1, 100), 6, clamp(@sheet.pool.target, 1, 6))"),
        ("dice-pool-count-hits", "successes(clamp(@sheet.pool.size, 1, 100), 6, clamp(@sheet.pool.hit, 1, 6))"),
        ("step-dice", "die(@sheet.attributes.strength)"),
        ("fudge-fate", "fate() + @sheet.approaches.careful"),
        ("2d6-pbta", "2d6 + @sheet.stats.cool"),
        ("2d20", "under(2, 20, clamp(@sheet.attributes.agility + @sheet.skills.athletics, 1, 20))"),
        ("year-zero-d6-pool", "successes(clamp(@sheet.attributes.strength, 1, 100), 6, 6)"),
        ("cards", "draw(52)"),
        ("custom", "1d20 + @sheet.resource"),
    ],
)
def test_roll_presets_use_their_fields(mechanic, formula):
    pkg = _ruleset(actor_types=("character",), mechanic=mechanic)
    actions = json.loads(pkg.files["rules/actions.gw.json"])["actions"]
    assert next(iter(actions.values()))["formula"] == formula


def test_step_die_select_stores_numeric_sides():
    pkg = _ruleset(actor_types=("character",), mechanic="step-dice")
    schema = json.loads(pkg.files["schemas/actors/character.schema.json"])
    strength = schema["properties"]["attributes"]["properties"]["strength"]
    assert strength == {"type": "integer", "enum": [4, 6, 8, 10, 12], "default": 6}
    assert '<option value="10">d10</option>' in pkg.files["sheets/character.html"]


@pytest.mark.parametrize("mechanic", [name for name in mechanic_ids() if name != "none"])
def test_every_roll_preset_executes_with_generated_defaults(mechanic):
    pkg = _ruleset(actor_types=("character",), mechanic=mechanic)
    schema = json.loads(pkg.files["schemas/actors/character.schema.json"])
    data = apply_schema_defaults(schema)
    action = next(iter(json.loads(pkg.files["rules/actions.gw.json"])["actions"].values()))
    result = evaluate(
        action["formula"],
        context={"core": {"name": "Test"}, "sheet": data, "item": {}},
        roller=lambda count, sides: [min(3, sides)] * count,
    )
    assert result.groups, mechanic


def test_multiple_actor_sheet_types(tmp_path):
    pkg = _ruleset(actor_types=("character", "monster", "npc"))
    ids = [a["id"] for a in pkg.manifest["provides"]["actorTypes"]]
    assert ids == ["character", "monster", "npc"]
    for tid in ids:
        assert f"sheets/{tid}.html" in pkg.files
        assert f"schemas/actors/{tid}.schema.json" in pkg.files
    loaded = load_package(_write(tmp_path, pkg), expected_id="my-rpg", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


def test_multiple_item_sheet_types(tmp_path):
    pkg = _ruleset(actor_types=("character",), item_types=("weapon", "spell", "consumable"))
    ids = [i["id"] for i in pkg.manifest["provides"]["itemTypes"]]
    assert ids == ["weapon", "spell", "consumable"]
    for tid in ids:
        assert f"sheets/{tid}.html" in pkg.files
    loaded = load_package(_write(tmp_path, pkg), expected_id="my-rpg", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


@pytest.mark.parametrize("mechanic", mechanic_ids())
@pytest.mark.parametrize("html_sheets", [False, True], ids=["json", "html"])
def test_each_core_mechanic_generates_valid_package(tmp_path, mechanic, html_sheets):
    pkg = _ruleset(
        package_id="demo",
        html_sheets=html_sheets,
        actor_types=("character",),
        item_types=("item",),
        mechanic=mechanic,
    )
    loaded = load_package(_write(tmp_path, pkg), expected_id="demo", expected_kind_root="rulesets")
    assert loaded.ok, (mechanic, loaded.validation.errors)


def test_mechanic_example_lands_on_character_sheet():
    pkg = _ruleset(actor_types=("character", "npc"), mechanic="d20-attribute-modifier-skill")
    character = pkg.files["sheets/character.html"]
    npc = pkg.files["sheets/npc.html"]
    assert 'data-bind="system.attributes.strength"' in character
    assert 'data-action="strength-check"' in character
    # Non-mechanic actors get a generic sheet without the mechanic fields.
    assert "system.attributes.strength" not in npc
    schema = json.loads(pkg.files["schemas/actors/character.schema.json"])
    assert {"attributes", "skills"} <= set(schema["properties"])


def test_mechanic_falls_back_to_first_actor_when_no_character():
    pkg = _ruleset(actor_types=("monster", "npc"), mechanic="d20-attribute-modifier")
    assert 'data-bind="system.attributes.strength"' in pkg.files["sheets/monster.html"]
    assert "system.attributes.strength" not in pkg.files["sheets/npc.html"]


def test_custom_actor_type_is_normalized(tmp_path):
    pkg = _ruleset(actor_types=("Star Ship", "MECHA"))
    ids = [a["id"] for a in pkg.manifest["provides"]["actorTypes"]]
    assert ids == ["star-ship", "mecha"]
    assert "sheets/star-ship.html" in pkg.files
    loaded = load_package(_write(tmp_path, pkg), expected_id="my-rpg", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


def test_custom_item_type_is_normalized():
    pkg = _ruleset(actor_types=("character",), item_types=("Vehicle Module", "Cyber-Ware"))
    ids = [i["id"] for i in pkg.manifest["provides"]["itemTypes"]]
    assert ids == ["vehicle-module", "cyber-ware"]


def test_duplicate_ids_after_normalization_are_collapsed():
    pkg = _ruleset(actor_types=("Character", "character", "CHARACTER"))
    ids = [a["id"] for a in pkg.manifest["provides"]["actorTypes"]]
    assert ids == ["character"]


def test_no_package_id_in_manifest_paths():
    pkg = _ruleset(package_id="sexto-elemento-rpg-oficial", actor_types=("character",), item_types=("weapon",))
    # Every generated file path is package-relative and never prefixed with id.
    for path in pkg.files:
        assert not path.startswith("sexto-elemento-rpg-oficial")
        assert "sexto-elemento-rpg-oficial/" not in path


def test_all_manifest_paths_exist_in_generated_files():
    from app.engine.sdk.package_manifest import PackageManifest

    pkg = _ruleset(actor_types=("character", "npc"), item_types=("weapon",), mechanic="2d6-pbta")
    manifest = PackageManifest.from_dict(pkg.manifest)
    for path in manifest.referenced_paths():
        assert path in pkg.files, path


# --- legacy flag path (back-compat) -----------------------------------------


def test_legacy_boolean_intent_still_generates_declarative_sheet(tmp_path):
    pkg = build_package(
        package_id="legacy", name="Legacy", kind="ruleset",
        intent=Intent(has_characters=True, has_monsters=True, has_items=True, has_sheets=True),
    )
    actor_ids = {a["id"] for a in pkg.manifest["provides"]["actorTypes"]}
    assert actor_ids == {"character", "monster"}
    assert declared_sheet_type_ids(
        Intent(has_characters=True, has_monsters=True, has_items=True, has_sheets=True)
    ) == ["character", "monster", "item"]
    loaded = load_package(_write(tmp_path, pkg), expected_id="legacy", expected_kind_root="rulesets")
    assert loaded.ok, loaded.validation.errors


def test_new_writes_grouped_kind_layout(tmp_path):
    from app.cli import build_parser

    args = build_parser().parse_args(
        ["ruleset", "new", "my-rpg", "--name", "My RPG", "--actor-types", "character",
         "--yes", "--output-dir", str(tmp_path)]
    )
    assert args.func(args) == 0
    assert (tmp_path / "rulesets" / "my-rpg" / "manifest.json").is_file()
    assert not (tmp_path / "my-rpg").exists()
