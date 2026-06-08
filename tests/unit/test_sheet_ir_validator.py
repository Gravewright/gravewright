from __future__ import annotations

from app.engine.sheets.sheet_ir_validator import validate_sheet_ir


def test_valid_layout_passes():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "tabs",
            "tabs": [
                {"id": "main", "label": "Main", "children": [
                    {"type": "section", "label": "Combat", "children": [
                        {"type": "resourceField", "label": "HP", "valuePath": "sheet.hp.value", "maxPath": "sheet.hp.max"},
                        {"type": "rollButton", "label": "Init", "action": "roll.initiative"},
                    ]},
                ]},
            ],
        },
    }
    assert validate_sheet_ir(ir) == []


def test_not_object():
    assert validate_sheet_ir("nope") == ["game.sheet_ir.errors.not_object"]


def test_wrong_kind_and_missing_body():
    errors = validate_sheet_ir({"kind": "weird"})
    assert "game.sheet_ir.errors.kind" in errors
    assert "game.sheet_ir.errors.body_required" in errors


def test_unknown_component_flagged():
    ir = {"kind": "actorSheet", "body": {"type": "section", "children": [{"type": "hologram"}]}}
    assert "game.sheet_ir.errors.unknown_component" in validate_sheet_ir(ir)


def test_ability_card_component_passes():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {
                    "type": "abilityCard",
                    "label": "Força",
                    "abbr": "FOR",
                    "scorePath": "sheet.abilities.str.score",
                    "modPath": "sheet.abilities.str.mod",
                    "rollAction": "roll.check.str",
                    "variant": "dnd5e",
                }
            ],
        },
    }
    assert validate_sheet_ir(ir) == []


def test_ability_card_requires_score_and_mod_paths():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {"type": "abilityCard", "label": "Força"}
            ],
        },
    }
    errors = validate_sheet_ir(ir)
    assert "game.sheet_ir.errors.ability_card_score_path" in errors
    assert "game.sheet_ir.errors.ability_card_mod_path" in errors


def test_ability_card_action_menu_interaction_passes():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {
                    "type": "abilityCard",
                    "label": "Força",
                    "scorePath": "sheet.abilities.str.score",
                    "modPath": "sheet.abilities.str.mod",
                    "interaction": {
                        "type": "actionMenu",
                        "title": "Força",
                        "items": [
                            {"label": "Teste", "action": "roll.check.str", "dialog": "roll"},
                            {"label": "Save", "action": "roll.save.str", "icon": "shield"},
                        ],
                    },
                }
            ],
        },
    }
    assert validate_sheet_ir(ir) == []


def test_ability_card_rejects_invalid_interaction():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {
                    "type": "abilityCard",
                    "label": "Força",
                    "scorePath": "sheet.abilities.str.score",
                    "modPath": "sheet.abilities.str.mod",
                    "interaction": {"type": "actionMenu", "items": [{"label": "Sem ação"}]},
                }
            ],
        },
    }
    errors = validate_sheet_ir(ir)
    assert "game.sheet_ir.errors.interaction_item_target" in errors


def test_ability_card_roll_dialog_schema_passes():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {
                    "type": "abilityCard",
                    "label": "Força",
                    "scorePath": "sheet.abilities.str.score",
                    "modPath": "sheet.abilities.str.mod",
                    "interaction": {
                        "type": "actionMenu",
                        "items": [
                            {
                                "label": "Teste",
                                "action": "roll.check.str",
                                "dialog": {
                                    "type": "roll",
                                    "fields": [
                                        {
                                            "id": "mode",
                                            "type": "select",
                                            "label": "Modo",
                                            "options": [
                                                {"value": "normal", "label": "Normal"},
                                                {"value": "advantage", "label": "Vantagem"},
                                            ],
                                        },
                                        {"id": "extraDice", "type": "diceList", "label": "Dados extras"},
                                        {"id": "visibility", "type": "visibility", "label": "Visibilidade"},
                                    ],
                                },
                            }
                        ],
                    },
                }
            ],
        },
    }
    assert validate_sheet_ir(ir) == []


def test_roll_dialog_schema_rejects_invalid_fields():
    ir = {
        "kind": "actorSheet",
        "body": {
            "type": "section",
            "children": [
                {
                    "type": "abilityCard",
                    "label": "Força",
                    "scorePath": "sheet.abilities.str.score",
                    "modPath": "sheet.abilities.str.mod",
                    "interaction": {
                        "type": "actionMenu",
                        "items": [
                            {
                                "label": "Teste",
                                "action": "roll.check.str",
                                "dialog": {"type": "roll", "fields": [{"type": "select"}]},
                            }
                        ],
                    },
                }
            ],
        },
    }
    errors = validate_sheet_ir(ir)
    assert "game.sheet_ir.errors.roll_dialog_field_id" in errors
    assert "game.sheet_ir.errors.roll_dialog_select_options" in errors


def test_modifier_builder_component_validates_catalog():
    from app.engine.sheets.sheet_ir_validator import validate_sheet_ir

    valid = {
        "kind": "itemSheet",
        "body": {
            "type": "modifierBuilder",
            "path": "sheet.modifiers",
            "targets": [
                {
                    "id": "roll.attack",
                    "label": "Ataques",
                    "operations": [{"id": "add_dice", "label": "Adicionar dado", "valueType": "dice"}],
                }
            ],
        },
    }
    assert validate_sheet_ir(valid) == []

    invalid = {
        "kind": "itemSheet",
        "body": {"type": "modifierBuilder", "path": "sheet.modifiers", "targets": []},
    }
    assert "game.sheet_ir.errors.modifier_builder_targets" in validate_sheet_ir(invalid)
