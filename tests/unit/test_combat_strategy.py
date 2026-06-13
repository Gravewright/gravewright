from __future__ import annotations

from app.engine.combat.turn_order_service import TurnOrderService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_actor, seed_campaign, seed_system, seed_user


def test_dnd5e_combat_config_uses_formula_sort(db):
    gm_id = seed_user(name="GM", email="gm-combat-strategy@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")

    fiona = seed_actor(
        campaign_id,
        gm_id,
        name="Fiona",
        system_id=system_id,
        data={"combat": {"initiative": 20}, "abilities": {"dex": {"score": 18}}},
    )
    monster = seed_actor(
        campaign_id,
        gm_id,
        name="Monstro Modelo",
        actor_type="monster",
        system_id=system_id,
        data={"combat": {"initiative": -5}, "abilities": {"dex": {"score": 8}}},
    )

    service = TurnOrderService()
    started = service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[fiona, monster])
    assert started.success
    assert started.config["turnOrder"]["strategy"] == "formula_sort"
    assert len(started.participants) == 2

    rolled = service.roll_initiative(campaign_id=campaign_id, user_id=gm_id)
    assert rolled.success
    assert rolled.participants[0]["initiative_data"]["kind"] == "formula"
    assert rolled.participants[0]["initiative_label"]
    assert rolled.state_payload()["current"]["id"] == rolled.participants[0]["id"]


def test_combat_state_visible_to_player(db):
    gm_id = seed_user(name="GM", email="gm-combat-player@test.com")
    player_id = seed_user(name="Player", email="player-combat-player@test.com")
    campaign_id = seed_campaign(gm_id)
    from tests.conftest import seed_member

    seed_member(campaign_id, player_id, "player")
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor_id = seed_actor(campaign_id, gm_id, name="Fiona", system_id=system_id, data={"combat": {"initiative": 2}})

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id]).success
    player_state = service.get_state(campaign_id=campaign_id, user_id=player_id)
    assert player_state.success
    assert player_state.is_active is True
    assert player_state.participants[0]["name"] == "Fiona"


def test_combat_config_paths_are_registered(db):
    gm_id = seed_user(name="GM", email="gm-combat-config-path@test.com")
    systems = SystemInstallService()
    assert systems.install(package_id="dnd5e", user_id=gm_id).success
    manifest = systems.get_manifest("dnd5e")
    assert manifest is not None
    assert "rules/combat.gw.json" in manifest.referenced_paths()


def test_combat_config_exposes_canonical_initiative_api(db):
    gm_id = seed_user(name="GM", email="gm-combat-initiative-api@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor_id = seed_actor(campaign_id, gm_id, name="Fiona", system_id=system_id, data={"combat": {"initiative": 2}})

    state = TurnOrderService().start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])

    assert state.success
    assert state.config["initiative"]["mode"] == "individual"
    assert state.config["initiative"]["roll"]["actionId"] == "roll.initiative"
    assert state.config["initiative"]["roll"]["formula"] == "1d20 + @sheet.combat.initiative"
    assert state.config["initiative"]["sort"]["direction"] == "desc"
                                                                    
    assert state.config["initiativeRoll"]["actionId"] == "roll.initiative"


def test_canonical_initiative_formula_drives_bulk_roll_even_when_action_formula_differs(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 10)
    gm_id = seed_user(name="GM", email="gm-combat-canonical-formula@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor_id = seed_actor(campaign_id, gm_id, name="Fiona", system_id=system_id, data={"combat": {"initiative": 7}})

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id]).success
    rolled = service.roll_initiative(campaign_id=campaign_id, user_id=gm_id)

    assert rolled.success
    assert rolled.participants[0]["initiative_label"] == "17"
    assert rolled.participants[0]["initiative_data"]["source"]["kind"] == "initiative"


def test_dnd5e_initiative_config_exposes_dnd5e_appearance(db):
    gm_id = seed_user(name="GM", email="gm-combat-dnd-appearance@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor_id = seed_actor(campaign_id, gm_id, name="Fiona", system_id=system_id)

    state = TurnOrderService().start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])

    assert state.success
    assert state.config["initiative"]["label"] == "D&D 5e Initiative"
    assert state.config["initiative"]["appearance"]["theme"] == "dnd5e"
    assert state.config["initiative"]["appearance"]["die"] == "d20"
    assert state.config["initiative"]["appearance"]["rollMonstersLabel"] == "Monsters only"


def test_dnd5e_combat_ui_is_defined_by_system_package(db):
    gm_id = seed_user(name="GM", email="gm-combat-system-ui@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor_id = seed_actor(campaign_id, gm_id, name="Fiona", system_id=system_id)

    state = TurnOrderService().start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])

    assert state.success
    combat_ui = state.config["ui"]["combat"]
    assert combat_ui["skin"] == "dnd5e"
    assert combat_ui["palette"]["accent"] == "#b88a44"
    assert combat_ui["palette"]["accentStrong"] == "#ffe4a3"
    assert combat_ui["palette"]["danger"] == "#9f1d1d"
    assert combat_ui["palette"]["surfaceRaised"] == "#3a211a"
    assert combat_ui["initiative"]["icon"] == "ph-dice-five"
    assert combat_ui["initiative"]["rollAllLabel"] == "Roll initiative"
    assert combat_ui["initiative"]["rollMonstersLabel"] == "Roll monsters"
    assert combat_ui["statusLabels"]["next"] == "Next"


def test_roll_monster_initiative_only_updates_monster_participants(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 10)
    gm_id = seed_user(name="GM", email="gm-combat-monster-roll@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id, package_id="dnd5e")
    hero_id = seed_actor(
        campaign_id,
        gm_id,
        name="Fiona",
        actor_type="character",
        system_id=system_id,
        data={"combat": {"initiative": 4}, "abilities": {"dex": {"score": 18}}},
    )
    monster_id = seed_actor(
        campaign_id,
        gm_id,
        name="Monstro Modelo",
        actor_type="monster",
        system_id=system_id,
        data={"combat": {"initiative": 2}, "abilities": {"dex": {"score": 12}}},
    )

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[hero_id, monster_id]).success
    rolled = service.roll_monster_initiative(campaign_id=campaign_id, user_id=gm_id)

    assert rolled.success
    by_actor = {participant["actor_id"]: participant for participant in rolled.participants}
    assert by_actor[hero_id]["initiative_label"] == ""
    assert by_actor[monster_id]["initiative_label"] == "12"
    assert by_actor[monster_id]["initiative_data"]["scope"] == "monsters"
