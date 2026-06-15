from __future__ import annotations

from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import seed_user

HELPERS = {"abilityMod": {"args": ["score"], "expression": "floor((score - 10) / 2)"}}
DERIVED = {
    "character": {
        "sheet.attributes.str.mod": "abilityMod(@sheet.attributes.str.score)",
        "sheet.attributes.dex.mod": "abilityMod(@sheet.attributes.dex.score)",
        "sheet.initiative": "@sheet.attributes.dex.mod",
        "sheet.defense": "@sheet.ac",
    }
}


def test_apply_derived_computes_dependent_fields():
    data = {"ac": 15, "attributes": {"str": {"score": 14}, "dex": {"score": 16}}}
    out = apply_derived(actor_type="character", data=data, derived_rules=DERIVED, helpers=HELPERS)

    assert out["attributes"]["str"]["mod"] == 2
    assert out["attributes"]["dex"]["mod"] == 3
    assert out["initiative"] == 3
    assert out["defense"] == 15
                                       
    assert "mod" not in data["attributes"]["str"]


def test_token_view_resolves_paths():
    mappings = {
        "character": {
            "name": "core.name",
            "bars": {"hp": {"value": "sheet.hp.value", "max": "sheet.hp.max"}},
            "initiative": "sheet.initiative",
            "defense": "sheet.ac",
        }
    }
    view = resolve_token_view(
        actor_type="character",
        sheet_data={"hp": {"value": 12, "max": 30}, "ac": 15, "initiative": 3},
        core={"name": "Aria"},
        token_mappings=mappings,
    )
    assert view == {
        "name": "Aria",
        "bars": {"hp": {"value": 12, "max": 30}},
        "initiative": 3,
        "defense": 15,
    }


def test_rules_registry_reads_bundled_dnd5e(db):
    owner_id = seed_user(name="Owner", email="owner-rules@test.com")
    svc = PackageInstallService()
    assert svc.install(package_id="dnd5e", user_id=owner_id).success
    assert svc.enable(package_id="dnd5e").success

    rules = SystemRulesService()
    assert "abilityMod" in rules.get_helpers("dnd5e")
    assert "roll.initiative" in rules.get_actions("dnd5e")
    assert rules.get_action("dnd5e", "resource.hp.damage")["type"] == "patch"
    assert "character" in rules.get_token_mappings("dnd5e")
    assert "character" in rules.get_derived("dnd5e")
