from __future__ import annotations

from app.engine.actors.actor_service import ActorService
from app.engine.combat.turn_order_service import TurnOrderService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_scene
from tests.conftest import seed_actor, seed_campaign, seed_user


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-combat-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    systems = PackageInstallService()
    assert systems.install(package_id="dnd5e", user_id=gm_id).success
    assert systems.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Fiona",
    )
    assert actor.success
    return gm_id, campaign_id, actor.actor_id


def test_start_and_advance_round_decrements_round_effects(db):
    gm_id, campaign_id, actor_id = _setup("rounds")
    assert SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "content_pack_entry", "pack_id": "dnd5e-conditions", "entry_id": "bless"},
        drop_zone="effects",
    ).success

    service = TurnOrderService()
    started = service.start(campaign_id=campaign_id, user_id=gm_id)
    assert started.success
    assert started.is_active is True
    assert started.round_number == 1

    advanced = service.next_round(campaign_id=campaign_id, user_id=gm_id)
    assert advanced.success
    assert advanced.round_number == 2
    assert advanced.updated_actors[0]["actor_id"] == actor_id

    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["effects"][0]["duration"]["remaining"] == 9
    assert data["effects"][0]["enabled"] is True


def test_round_effect_expires_and_disables(db):
    gm_id, campaign_id, actor_id = _setup("expires")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={
            "effects": [
                {
                    "id": "effect_once",
                    "type": "effect",
                    "name": "One Round",
                    "enabled": True,
                    "duration": {"type": "rounds", "remaining": 1},
                    "data": {"category": "buff", "modifiers": []},
                }
            ]
        },
    )

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id).success
    advanced = service.next_round(campaign_id=campaign_id, user_id=gm_id)

    assert advanced.success
    assert advanced.expired_effects[0]["effect_id"] == "effect_once"
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["effects"][0]["duration"]["remaining"] == 0
    assert data["effects"][0]["enabled"] is False


def test_turn_start_applies_damage_over_time(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)            
    gm_id, campaign_id, actor_id = _setup("dot")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={
            "hp": {"value": 20, "max": 20},
            "effects": [
                {
                    "id": "burning",
                    "type": "effect",
                    "name": "Em Chamas",
                    "enabled": True,
                    "duration": {"type": "rounds", "remaining": 3},
                    "data": {
                        "category": "condition",
                        "modifiers": [
                            {
                                "target": "damage.self",
                                "operation": "damage_over_time",
                                "value": "1d6",
                                "damageType": "fire",
                                "label": "Em Chamas",
                            }
                        ],
                    },
                }
            ],
        },
    )

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id]).success
    assert service.roll_initiative(campaign_id=campaign_id, user_id=gm_id).success
                                                                             
    advanced = service.next_turn(campaign_id=campaign_id, user_id=gm_id)

    assert advanced.success
    tick = advanced.effect_ticks[0]
    assert tick["actor_id"] == actor_id
    assert tick["actor_name"] == "Fiona"
    assert tick["operation"] == "damage_over_time"
    assert tick["amount"] == 4
    assert tick["damage_type"] == "fire"
    assert tick["resource_path"] == "hp.value"                                            
    assert tick["value_after"] == 16

    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["hp"]["value"] == 16                        
                                                                                      
    assert data["effects"][0]["duration"]["remaining"] == 3


def test_add_participants_accepts_multiple_tokens_from_same_actor(db):
    gm_id, campaign_id, actor_id = _setup("token-participants")
    scene = seed_scene(campaign_id)
    tokens = [
        TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=index, grid_y=0, name=f"Monstro Modelo {index + 1}")
        for index in range(3)
    ]

    service = TurnOrderService()
    result = service.add_participants(
        campaign_id=campaign_id,
        user_id=gm_id,
        actor_ids=[actor_id],
        token_ids=[token["id"] for token in tokens],
    )

    assert result.success
    assert len(result.participants) == 3
    assert {participant["token_id"] for participant in result.participants} == {token["id"] for token in tokens}


def test_record_initiative_roll_updates_matching_token_participant(db):
    gm_id, campaign_id, actor_id = _setup("token-initiative")
    scene = seed_scene(campaign_id)
    token_a = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0, name="Monstro Modelo A")
    token_b = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=0, name="Monstro Modelo B")

    service = TurnOrderService()
    assert service.add_participants(
        campaign_id=campaign_id,
        user_id=gm_id,
        actor_ids=[],
        token_ids=[token_a["id"], token_b["id"]],
    ).success

    service.record_initiative_roll(
        campaign_id=campaign_id,
        actor_id=actor_id,
        token_id=token_b["id"],
        user_id=gm_id,
        total=17,
        metadata={"actionId": "roll.initiative"},
    )
    state = service.get_state(campaign_id=campaign_id, user_id=gm_id)

    by_token = {participant["token_id"]: participant for participant in state.participants}
    assert by_token[token_a["id"]]["initiative_label"] == ""
    assert by_token[token_b["id"]]["initiative_label"] == "17"


def test_plain_round_advance_does_not_apply_damage_over_time(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm_id, campaign_id, actor_id = _setup("dot-round")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={
            "hp": {"value": 20, "max": 20},
            "effects": [
                {
                    "id": "burning",
                    "name": "Em Chamas",
                    "enabled": True,
                    "duration": {"type": "rounds", "remaining": 3},
                    "data": {
                        "modifiers": [
                            {"target": "damage.self", "operation": "damage_over_time", "value": "1d6"}
                        ]
                    },
                }
            ],
        },
    )

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id]).success
    advanced = service.next_round(campaign_id=campaign_id, user_id=gm_id)

    assert advanced.effect_ticks == []                                      
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["hp"]["value"] == 20             
    assert data["effects"][0]["duration"]["remaining"] == 2                        


def test_roll_participant_initiative_uses_system_action(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 15)              
    gm_id = seed_user(name="GM", email="gm-combat-dnd5e-init@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = PackageInstallService().install(package_id="dnd5e", user_id=gm_id).package_id
    assert system_id
    assert PackageInstallService().enable(package_id="dnd5e").success
    from app.business.campaigns.campaign_system_service import CampaignSystemService

    assert CampaignSystemService().assign_to_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id=system_id,
    ).success
    actor_id = seed_actor(
        campaign_id,
        gm_id,
        name="Delver",
        system_id=system_id,
        data={"init": 2},
    )

    service = TurnOrderService()
    state = service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])
    participant_id = state.participants[0]["id"]
    rolled = service.roll_participant_initiative(
        campaign_id=campaign_id,
        user_id=gm_id,
        participant_id=participant_id,
    )

    assert rolled.success
    assert rolled.config["turnOrder"]["strategy"] == "formula_sort"
    assert rolled.participants[0]["initiative_label"] == "15"
    assert rolled.participants[0]["initiative_data"]["source"]["kind"] == "initiative"


def test_roll_participant_initiative_uses_unlinked_token_instance_sheet(db, monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 10)              
    gm_id, campaign_id, actor_id = _setup("token-instance-init")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={"abilities": {"dex": {"score": 10}}, "init_misc": 0},
    )
    scene = seed_scene(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"],
        actor_id=actor_id,
        grid_x=0,
        grid_y=0,
        name="Monstro Modelo Fast",
        actor_link_mode="unlinked",
        overrides={
            "_actor_instance": {
                "source_actor_id": actor_id,
                "name": "Monstro Modelo Fast",
                "type": "character",
                "system_id": "dnd5e",
                "version": 1,
                "data": {"abilities": {"dex": {"score": 20}}, "init_misc": 0},
            }
        },
    )

    service = TurnOrderService()
    state = service.add_participants(
        campaign_id=campaign_id,
        user_id=gm_id,
        actor_ids=[],
        token_ids=[token["id"]],
    )
    participant_id = state.participants[0]["id"]
    rolled = service.roll_participant_initiative(
        campaign_id=campaign_id,
        user_id=gm_id,
        participant_id=participant_id,
    )

    assert rolled.success
    assert rolled.participants[0]["initiative_label"] == "15"                               


def test_combat_participants_include_portrait_urls(db):
    gm_id, campaign_id, actor_id = _setup("portrait")
    from app.persistence.database import engine_begin

    with engine_begin() as conn:
        conn.exec_driver_sql(
            "UPDATE actors_core SET portrait_asset_id = ?, token_asset_id = ?, updated_at = updated_at + 1 WHERE id = ?",
            ("actors/fiona.webp", "actors/fiona-token.webp", actor_id),
        )

    service = TurnOrderService()
    state = service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])

    assert state.success
    assert state.participants[0]["portrait_url"].startswith(f"/game/actor/{actor_id}/image/token")
    assert state.participants[0]["token_asset_url"].startswith(f"/game/actor/{actor_id}/image/token")


def test_active_turn_payload_marks_current_waiting_and_acted(db):
    gm_id, campaign_id, actor_id = _setup("turn-payload")
    actor_b = seed_actor(campaign_id, gm_id, name="Borin", system_id="dnd5e")
    actor_c = seed_actor(campaign_id, gm_id, name="Cora", system_id="dnd5e")

    service = TurnOrderService()
    started = service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id, actor_b, actor_c])

    assert started.success
    payload = started.state_payload()
    assert payload["round"] == 1
    assert payload["turn_position"] == 1
    assert payload["turn_count"] == 3
    assert payload["current_participant_id"] == started.participants[0]["id"]
    assert payload["next_participant_id"] == started.participants[1]["id"]
    assert [participant["turn_status"] for participant in started.participants] == ["current", "waiting", "waiting"]
    assert [participant["is_next"] for participant in started.participants] == [False, True, False]

    advanced = service.next_turn(campaign_id=campaign_id, user_id=gm_id)
    assert advanced.success
    assert advanced.state_payload()["turn_position"] == 2
    assert advanced.state_payload()["next_participant_id"] == advanced.participants[2]["id"]
    assert [participant["turn_status"] for participant in advanced.participants] == ["acted", "current", "waiting"]
    assert [participant["is_next"] for participant in advanced.participants] == [False, False, True]


def test_previous_turn_wraps_to_previous_round_last_participant(db):
    gm_id, campaign_id, actor_id = _setup("turn-previous")
    actor_b = seed_actor(campaign_id, gm_id, name="Borin", system_id="dnd5e")

    service = TurnOrderService()
    assert service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id, actor_b]).success
    assert service.next_turn(campaign_id=campaign_id, user_id=gm_id).success
    wrapped = service.next_turn(campaign_id=campaign_id, user_id=gm_id)
    assert wrapped.round_number == 2
    assert wrapped.state_payload()["turn_index"] == 0

    rewound = service.previous_turn(campaign_id=campaign_id, user_id=gm_id)
    assert rewound.success
    assert rewound.round_number == 1
    assert rewound.state_payload()["turn_index"] == 1
    assert rewound.state_payload()["next_participant_id"] == rewound.participants[0]["id"]
    assert rewound.participants[1]["is_current"] is True
    assert rewound.participants[0]["is_next"] is True


def test_remove_participant_clamps_active_turn_index(db):
    gm_id, campaign_id, actor_id = _setup("turn-remove")
    actor_b = seed_actor(campaign_id, gm_id, name="Borin", system_id="dnd5e")
    actor_c = seed_actor(campaign_id, gm_id, name="Cora", system_id="dnd5e")

    service = TurnOrderService()
    started = service.start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id, actor_b, actor_c])
    assert started.success
    assert service.set_turn(campaign_id=campaign_id, user_id=gm_id, turn_index=2).success

    removed = service.remove_participant(
        campaign_id=campaign_id,
        user_id=gm_id,
        participant_id=started.participants[2]["id"],
    )

    assert removed.success
    assert removed.state_payload()["turn_index"] == 1
    assert removed.state_payload()["turn_count"] == 2
    assert sum(1 for participant in removed.participants if participant["is_current"]) == 1
    assert removed.participants[1]["is_current"] is True


def test_combat_participants_include_system_hp_resource(db):
    gm_id, campaign_id, actor_id = _setup("participant-hp")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={"hp": {"value": 7, "max": 20}},
    )

    state = TurnOrderService().start(campaign_id=campaign_id, user_id=gm_id, actor_ids=[actor_id])

    assert state.success
    hp = state.participants[0]["resources"]["hp"]
    assert hp["value"] == 7
    assert hp["max"] == 20
    assert hp["percent"] == 35
