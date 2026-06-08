from __future__ import annotations


from app.domain.tokens import TokenActorLinkMode
from app.domain.tokens import TokenConditionKind
from app.domain.tokens import TokenDisposition
from app.persistence.repositories.token_condition_repository import TokenConditionRepository
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_scene
from tests.conftest import seed_actor
from tests.conftest import seed_user


                                                                             
         
                                                                             

def make_stack(db):
    gm_id = seed_user(email="token-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Monstro Modelo")
    return campaign_id, scene, actor_id


                                                                             
                                
                                                                             

def test_create_returns_hydrated_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()

    token = repo.create(
        scene_id=scene["id"],
        actor_id=actor_id,
        grid_x=5,
        grid_y=3,
        disposition=TokenDisposition.HOSTILE,
        actor_link_mode=TokenActorLinkMode.UNLINKED,
    )

    assert token["id"] is not None
    assert token["scene_id"] == scene["id"]
    assert token["actor_id"] == actor_id
    assert token["grid_x"] == 5
    assert token["grid_y"] == 3
    assert token["disposition"] == TokenDisposition.HOSTILE
    assert token["actor_link_mode"] == TokenActorLinkMode.UNLINKED
    assert token["version"] == 1
    assert token["hidden"] == 0
    assert token["locked"] == 0
    assert token["overrides"] == {}
    assert token["controlled_by_user_ids"] == []


def test_create_with_name_override(db):
    _campaign_id, scene, actor_id = make_stack(db)

    token = TokenRepository().create(
        scene_id=scene["id"],
        actor_id=actor_id,
        grid_x=0,
        grid_y=0,
        name="Monstro Modelo Guard",
    )

    assert token["name"] == "Monstro Modelo Guard"


def test_create_without_sheet(db):
    gm_id = seed_user(email="nosheet@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    token = TokenRepository().create(
        scene_id=scene["id"],
        actor_id=None,
        grid_x=0,
        grid_y=0,
    )

    assert token["actor_id"] is None


def test_get_by_id_returns_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    created = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=2)

    fetched = repo.get_by_id(created["id"])

    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["grid_x"] == 1
    assert fetched["grid_y"] == 2


def test_get_by_id_returns_none_for_missing(db):
    _campaign_id, _scene, _actor_id = make_stack(db)
    assert TokenRepository().get_by_id("nonexistent") is None


def test_get_by_scene_and_id_validates_scene(db):
    gm_id = seed_user(email="two-scenes@test.com")
    campaign_id = seed_campaign(gm_id)
    scene_a = seed_scene(campaign_id, name="Scene A")
    scene_b = seed_scene(campaign_id, name="Scene B")
    actor_id = seed_actor(campaign_id, gm_id)

    repo = TokenRepository()
    token = repo.create(scene_id=scene_a["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    assert repo.get_by_scene_and_id(scene_id=scene_a["id"], token_id=token["id"]) is not None
    assert repo.get_by_scene_and_id(scene_id=scene_b["id"], token_id=token["id"]) is None


                                                                             
                               
                                                                             

def test_create_many_returns_all_tokens(db):
    _campaign_id, scene, actor_id = make_stack(db)

    specs = [
        {"scene_id": scene["id"], "actor_id": actor_id, "grid_x": i, "grid_y": 0}
        for i in range(3)
    ]
    tokens = TokenRepository().create_many(specs)

    assert len(tokens) == 3
    positions = [(t["grid_x"], t["grid_y"]) for t in tokens]
    assert positions == [(0, 0), (1, 0), (2, 0)]


def test_create_many_preserves_order(db):
    _campaign_id, scene, actor_id = make_stack(db)

    specs = [
        {"scene_id": scene["id"], "actor_id": actor_id, "grid_x": x, "grid_y": y, "name": f"tok-{i}"}
        for i, (x, y) in enumerate([(4, 1), (2, 3), (7, 0)])
    ]
    tokens = TokenRepository().create_many(specs)

    assert [t["name"] for t in tokens] == ["tok-0", "tok-1", "tok-2"]


def test_create_many_with_empty_list(db):
    tokens = TokenRepository().create_many([])
    assert tokens == []


                                                                             
                                 
                                                                             

def test_list_by_scene_returns_only_own_tokens(db):
    gm_id = seed_user(email="list-tokens@test.com")
    campaign_id = seed_campaign(gm_id)
    scene_a = seed_scene(campaign_id, name="A")
    scene_b = seed_scene(campaign_id, name="B")
    actor_id = seed_actor(campaign_id, gm_id)

    repo = TokenRepository()
    repo.create(scene_id=scene_a["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    repo.create(scene_id=scene_a["id"], actor_id=actor_id, grid_x=1, grid_y=0)
    repo.create(scene_id=scene_b["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    assert len(repo.list_by_scene(scene_a["id"])) == 2
    assert len(repo.list_by_scene(scene_b["id"])) == 1


                                                                             
                        
                                                                             

def test_move_updates_position_and_bumps_version(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    updated = repo.move(token_id=token["id"], grid_x=10, grid_y=7)

    assert updated["grid_x"] == 10
    assert updated["grid_y"] == 7
    assert updated["version"] == token["version"] + 1


def test_move_unknown_token_returns_none(db):
    _campaign_id, _scene, _actor_id = make_stack(db)
    result = TokenRepository().move(token_id="bad-id", grid_x=0, grid_y=0)
    assert result is None


                                                                             
                                    
                                                                             

def test_update_overrides_persists_and_bumps_version(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    overrides = {"name": "Monstro Modelo Captain", "hp": {"value": 3, "max": 7}}
    updated = repo.update_overrides(token_id=token["id"], overrides=overrides)

    assert updated["overrides"] == overrides
    assert updated["version"] == token["version"] + 1


def test_update_overrides_replaces_previous(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    repo.update_overrides(token_id=token["id"], overrides={"hp": {"value": 5, "max": 10}})
    final = repo.update_overrides(token_id=token["id"], overrides={"hp": {"value": 2, "max": 10}})

    assert final["overrides"]["hp"]["value"] == 2
    assert final["version"] == token["version"] + 2


                                                                             
                              
                                                                             

def test_set_hidden_true_bumps_version(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    assert token["hidden"] == 0

    updated = repo.set_hidden(token_id=token["id"], hidden=True)

    assert updated["hidden"] == 1
    assert updated["version"] == token["version"] + 1


def test_set_hidden_false_reveals_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    repo.set_hidden(token_id=token["id"], hidden=True)

    revealed = repo.set_hidden(token_id=token["id"], hidden=False)

    assert revealed["hidden"] == 0
    assert revealed["version"] == token["version"] + 2


                                                                             
                          
                                                                             

def test_remove_deletes_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    removed = repo.remove(token_id=token["id"])

    assert removed is True
    assert repo.get_by_id(token["id"]) is None


def test_remove_returns_false_for_missing(db):
    _campaign_id, _scene, _actor_id = make_stack(db)
    assert TokenRepository().remove(token_id="nonexistent") is False


def test_tokens_cascade_delete_with_scene(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=0)

    from app.persistence.database import engine_begin
    with engine_begin() as conn:
        conn.exec_driver_sql("DELETE FROM scenes WHERE id = ?", (scene["id"],))

    assert repo.list_by_scene(scene["id"]) == []


                                                                             
                          
                                                                             

def test_add_condition_to_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    cond_repo = TokenConditionRepository()

    cond = cond_repo.add(
        token_id=token["id"],
        condition_id="poisoned",
        label="Poisoned",
        kind=TokenConditionKind.NEGATIVE,
    )

    assert cond["token_id"] == token["id"]
    assert cond["condition_id"] == "poisoned"
    assert cond["label"] == "Poisoned"
    assert cond["kind"] == TokenConditionKind.NEGATIVE


def test_add_condition_upserts_on_conflict(db):
    _campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    cond_repo = TokenConditionRepository()

    cond_repo.add(token_id=token["id"], condition_id="poisoned", label="Poisoned", duration=3)
    updated = cond_repo.add(token_id=token["id"], condition_id="poisoned", label="Poisoned", duration=1)

    assert updated["duration"] == 1
    assert len(cond_repo.list_by_token(token["id"])) == 1


def test_remove_condition(db):
    _campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    cond_repo = TokenConditionRepository()
    cond_repo.add(token_id=token["id"], condition_id="prone", label="Prone")

    removed = cond_repo.remove(token_id=token["id"], condition_id="prone")

    assert removed is True
    assert cond_repo.list_by_token(token["id"]) == []


def test_remove_missing_condition_returns_false(db):
    _campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    assert TokenConditionRepository().remove(token_id=token["id"], condition_id="stun") is False


def test_list_by_token_returns_conditions_in_order(db):
    _campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    cond_repo = TokenConditionRepository()
    cond_repo.add(token_id=token["id"], condition_id="poisoned", label="Poisoned")
    cond_repo.add(token_id=token["id"], condition_id="prone", label="Prone")

    conditions = cond_repo.list_by_token(token["id"])

    assert len(conditions) == 2
    assert conditions[0]["condition_id"] == "poisoned"
    assert conditions[1]["condition_id"] == "prone"


def test_list_by_tokens_batch(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    cond_repo = TokenConditionRepository()

    tok_a = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    tok_b = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=0)
    tok_c = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=2, grid_y=0)

    cond_repo.add(token_id=tok_a["id"], condition_id="poisoned", label="Poisoned")
    cond_repo.add(token_id=tok_a["id"], condition_id="prone", label="Prone")
    cond_repo.add(token_id=tok_b["id"], condition_id="stunned", label="Stunned")

    result = cond_repo.list_by_tokens([tok_a["id"], tok_b["id"], tok_c["id"]])

    assert len(result[tok_a["id"]]) == 2
    assert len(result[tok_b["id"]]) == 1
    assert len(result[tok_c["id"]]) == 0


def test_list_by_tokens_empty_input(db):
    assert TokenConditionRepository().list_by_tokens([]) == {}


def test_conditions_cascade_delete_with_token(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    cond_repo = TokenConditionRepository()

    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    cond_repo.add(token_id=token["id"], condition_id="poisoned", label="Poisoned")

    repo.remove(token_id=token["id"])

    assert cond_repo.list_by_token(token["id"]) == []


def test_move_with_expected_version_detects_stale_update(db):
    _campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    first = repo.move(
        token_id=token["id"],
        grid_x=1,
        grid_y=1,
        expected_version=token["version"],
    )
    stale = repo.move(
        token_id=token["id"],
        grid_x=2,
        grid_y=2,
        expected_version=token["version"],
    )
    stored = repo.get_by_id(token["id"])

    assert first is not None
    assert first["version"] == token["version"] + 1
    assert stale is None
    assert stored["grid_x"] == 1
    assert stored["grid_y"] == 1
