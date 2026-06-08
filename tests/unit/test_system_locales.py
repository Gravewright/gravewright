from __future__ import annotations

from app.engine.sheets.sheet_localizer import localize_layout
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.systems.system_locale_service import SystemLocaleService
from tests.conftest import seed_user


                                                                                


def test_localize_resolves_label_and_title_keys():
    layout = {
        "kind": "actorSheet",
        "titleKey": "sheet.title",
        "body": {
            "type": "section",
            "labelKey": "section.combat",
            "label": "fallback",
            "children": [
                {
                    "type": "selectField",
                    "labelKey": "field.mode",
                    "options": [{"value": "n", "labelKey": "opt.normal"}],
                }
            ],
        },
    }
    catalog = {
        "sheet.title": "Ficha",
        "section.combat": "Combate",
        "field.mode": "Modo",
        "opt.normal": "Normal",
    }
    out = localize_layout(layout, catalog)

    assert out["title"] == "Ficha"
    assert out["body"]["label"] == "Combate"
    assert out["body"]["children"][0]["label"] == "Modo"
    assert out["body"]["children"][0]["options"][0]["label"] == "Normal"
                                                      
    assert "label" not in layout["body"]["children"][0]
    assert layout["body"]["label"] == "fallback"


def test_localize_resolves_extended_display_keys():
    layout = {
        "type": "section",
        "children": [
            {
                "type": "textArea",
                "placeholderKey": "field.notes.placeholder",
                "emptyTextKey": "field.notes.empty",
            },
            {
                "type": "abilityCard",
                "abbrKey": "ability.str.abbr",
                "abilityKey": "ability.str.short",
            },
        ],
    }
    catalog = {
        "field.notes.placeholder": "Write notes",
        "field.notes.empty": "No notes",
        "ability.str.abbr": "STR",
        "ability.str.short": "Str",
    }

    out = localize_layout(layout, catalog)

    assert out["children"][0]["placeholder"] == "Write notes"
    assert out["children"][0]["emptyText"] == "No notes"
    assert out["children"][1]["abbr"] == "STR"
    assert out["children"][1]["ability"] == "Str"


def test_localize_keeps_existing_label_when_key_missing_and_empty_catalog_is_noop():
    layout = {"type": "section", "labelKey": "absent", "label": "Stays"}
    assert localize_layout(layout, {})["label"] == "Stays"
    assert localize_layout(layout, {"other": "x"})["label"] == "Stays"


                                                                                


def test_pick_locale_path_falls_back_exact_short_then_default():
    locales = {"en": "locales/en.json", "pt-BR": "locales/pt-BR.json"}
    pick = SystemLocaleService._pick_locale_path
    assert pick(locales, "pt-BR") == "locales/pt-BR.json"
    assert pick(locales, "pt") == "locales/en.json"                                    
    assert pick({"pt": "locales/pt.json"}, "pt-BR") == "locales/pt.json"             
    assert pick(locales, "fr") == "locales/en.json"                        
    assert pick({}, "en") == ""


                                                                                


def test_get_locale_reads_package_catalog(db):
    gm_id = seed_user(name="GM", email="gm-loc-1@test.com")
    service = SystemInstallService()
    assert service.install(package_id="dnd5e", user_id=gm_id).success
    assert service.enable(package_id="dnd5e").success

    catalog = SystemLocaleService().get_locale("dnd5e", "en")
    assert catalog.get("system.name") == "D&D 5e"

    assert SystemLocaleService().get_locale("does-not-exist", "en") == {}


def test_dnd5e_layout_uses_system_locale_catalog(db):
    gm_id = seed_user(name="GM", email="gm-loc-layout@test.com")
    service = SystemInstallService()
    assert service.install(package_id="dnd5e", user_id=gm_id).success
    assert service.enable(package_id="dnd5e").success

    layouts = SystemLayoutService()
    en_layout = layouts.get_actor_sheet(system_id="dnd5e", actor_type="character", locale="en")
    pt_layout = layouts.get_actor_sheet(system_id="dnd5e", actor_type="character", locale="pt-BR")

    assert en_layout is not None
    assert pt_layout is not None
    en_ability = en_layout["body"]["tabs"][0]["children"][0]["children"][0]
    pt_ability = pt_layout["body"]["tabs"][0]["children"][0]["children"][0]
    assert en_ability["label"] == "Strength"
    assert en_ability["abbr"] == "STR"
    assert pt_ability["label"] == "Força"
    assert pt_ability["abbr"] == "FOR"
