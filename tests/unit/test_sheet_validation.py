from __future__ import annotations

from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_validation import (
    apply_schema_defaults,
    merge_defaults,
    sanitize_write,
)
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_campaign, seed_user


                                                                                


def test_defaults_walk_nested_objects_and_arrays():
    schema = {
        "type": "object",
        "properties": {
            "level": {"type": "number", "default": 1},
            "hp": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "default": 10},
                    "mod": {"type": "number", "readOnly": True},
                },
            },
            "inventory": {"type": "array", "default": []},
            "notes": {"type": "string"},
        },
    }
    assert apply_schema_defaults(schema) == {"level": 1, "hp": {"value": 10}, "inventory": []}


def test_defaults_empty_for_missing_or_empty_schema():
    assert apply_schema_defaults(None) == {}
    assert apply_schema_defaults({}) == {}
    assert apply_schema_defaults({"type": "object", "properties": {}}) == {}


                                                                                


def test_merge_defaults_data_wins_and_fills_gaps():
    defaults = {"hp": {"value": 10, "max": 10}, "ac": 12}
    data = {"hp": {"value": 7}, "speed": 30}
    assert merge_defaults(defaults, data) == {
        "hp": {"value": 7, "max": 10},
        "ac": 12,
        "speed": 30,
    }


                                                                                

_SCHEMA = {
    "type": "object",
    "properties": {
        "hp": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "mod": {"type": "number", "readOnly": True},
            },
        },
        "name": {"type": "string"},
    },
}
_VALIDATION = {"sheet.hp.value": {"min": 0, "max": 50}}


def test_sanitize_clamps_min_and_max():
    clean, rejected = sanitize_write(_SCHEMA, _VALIDATION, {"hp.value": -5})
    assert clean == {"hp.value": 0}
    assert rejected == []

    clean, _ = sanitize_write(_SCHEMA, _VALIDATION, {"hp.value": 999})
    assert clean == {"hp.value": 50}


def test_sanitize_rejects_readonly_path():
    clean, rejected = sanitize_write(_SCHEMA, _VALIDATION, {"hp.mod": 4})
    assert clean == {}
    assert rejected == ["hp.mod"]


def test_sanitize_coerces_and_rejects_bad_types():
    clean, _ = sanitize_write(_SCHEMA, _VALIDATION, {"hp.value": "12"})
    assert clean == {"hp.value": 12.0}

    clean, _ = sanitize_write(_SCHEMA, _VALIDATION, {"name": 7})
    assert clean == {"name": "7"}

    clean, rejected = sanitize_write(_SCHEMA, _VALIDATION, {"hp.value": "nope"})
    assert clean == {}
    assert rejected == ["hp.value"]


def test_sanitize_passes_unknown_paths_and_no_schema():
                                                               
    clean, rejected = sanitize_write(_SCHEMA, {}, {"weapons.0.equipped": True})
    assert clean == {"weapons.0.equipped": True}
    assert rejected == []

                                                      
    clean, _ = sanitize_write(None, None, {"anything": 5})
    assert clean == {"anything": 5}


                                                                                


def _setup_dnd5e(prefix: str, actor_type: str = "character") -> tuple[str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    service = SystemInstallService()
    assert service.install(package_id="dnd5e", user_id=gm_id).success
    assert service.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type=actor_type,
        name="Aria" if actor_type == "character" else "Carnical Rastejante",
    )
    assert actor.success
    return gm_id, actor.actor_id


def test_created_actor_seeds_schema_defaults(db):
    gm_id, actor_id = _setup_dnd5e("sv-1")
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["level"] == 1
    assert data["abilities"]["str"]["score"] == 10
                                                          
    assert "mod" not in data["abilities"]["str"]


def test_created_monster_seeds_legendary_defaults(db):
    gm_id, actor_id = _setup_dnd5e("sv-monster", actor_type="monster")
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["legendary_resistance"] == 0
    assert data["legendary_actions_enabled"] == 0
    assert data["resistances"] == ""
    assert data["actions_text"] == ""
    assert data["legendary"] == ""


def test_patch_clamps_hp_and_blocks_readonly(db):
    gm_id, actor_id = _setup_dnd5e("sv-2")
    service = SheetDataService()

    service.patch_data(actor_id=actor_id, user_id=gm_id, patch={"hp.value": -5})
    assert service.get_data(actor_id=actor_id, user_id=gm_id).data["hp"]["value"] == 0

                                                                               
    result = service.patch_data(actor_id=actor_id, user_id=gm_id, patch={"abilities.str.mod": 99})
    assert not result.success
    assert result.error_key == "game.sheet_data.errors.empty_patch"
