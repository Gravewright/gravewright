from __future__ import annotations

from litestar.testing import TestClient

import app.engine.rules.formula_engine as formula_engine
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_actor_and_sheet_data_command_endpoints(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-actor-ep@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        created = client.post(
            "/game/actor",
            json={
                "csrf_token": csrf,
                "campaign_id": campaign_id,
                "system_id": "dnd5e",
                "type": "character",
                "name": "Aria",
            },
        )
        assert created.status_code == 201
        actor_id = created.json()["actor_id"]

        patched = client.post(
            "/game/actor/sheet-data/patch",
            json={"csrf_token": csrf, "actor_id": actor_id, "patch": {"hp.value": 12, "hp.max": 12}},
        )
        assert patched.status_code == 200
        assert patched.json()["version"] == 2

        fetched = client.get(f"/game/actor/{actor_id}/sheet-data")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["hp"]["value"] == 12
        assert fetched.json()["data"]["hp"]["max"] == 12


def test_actor_create_rejects_bad_csrf(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-actor-ep2@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    svc.install(package_id="dnd5e", user_id=gm_id)
    svc.enable(package_id="dnd5e")
                                                                               
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        client.set_session_data({"user_id": gm_id})
        resp = client.post(
            "/game/actor",
            json={
                "campaign_id": campaign_id,
                "system_id": "dnd5e",
                "type": "character",
                "name": "Aria",
            },
        )
    assert resp.status_code == 403


def test_action_and_roll_endpoints(db, monkeypatch):
    from main import app

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 15)
    gm_id = seed_user(name="GM", email="gm-action-ep@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        actor_id = client.post(
            "/game/actor",
            json={"csrf_token": csrf, "campaign_id": campaign_id,
                  "system_id": "dnd5e", "type": "character", "name": "Aria"},
        ).json()["actor_id"]

        client.post(
            "/game/actor/sheet-data/patch",
            json={"csrf_token": csrf, "actor_id": actor_id,
                  "patch": {"hp.value": 20, "hp.max": 30, "abilities.dex.score": 14}},
        )

                                      
        dmg = client.post(
            "/game/actor/action",
            json={"csrf_token": csrf, "actor_id": actor_id,
                  "action_id": "resource.hp.damage", "inputs": {"amount": 5}},
        )
        assert dmg.status_code == 200
        assert dmg.json()["changed_paths"] == ["sheet.hp.value"]

        fetched = client.get(f"/game/actor/{actor_id}/sheet-data")
        assert fetched.json()["data"]["hp"]["value"] == 15

                     
        roll = client.post(
            "/game/actor/action",
            json={"csrf_token": csrf, "actor_id": actor_id, "action_id": "roll.initiative"},
        )
        assert roll.status_code == 200
        assert roll.json()["type"] == "roll"
        assert roll.json()["total"] == 17                      
        assert roll.json()["metadata"]["actionId"] == "roll.initiative"
        assert roll.json()["metadata"]["actorId"] == actor_id
        assert roll.json()["metadata"]["source"] == {"kind": "actor", "actorId": actor_id}
        assert roll.json()["metadata"]["formula"]["base"] == "1d20 + @sheet.init"
        assert roll.json()["metadata"]["presentation"]["chatCard"] == "check"
        assert roll.json()["metadata"]["rendered"]["chatCard"]["id"] == "check"
        assert roll.json()["metadata"]["rendered"]["chatCard"]["total"] == 17
        assert roll.json()["metadata"]["rendered"]["rollToast"]["id"] == "check"

                       
        raw = client.post(
            "/game/actor/roll",
            json={"csrf_token": csrf, "actor_id": actor_id, "formula": "1d20", "label": "Test"},
        )
        assert raw.status_code == 200
        assert raw.json()["total"] == 15


def test_actor_sheet_modal_and_bundle_endpoints(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-sheet-modal@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        actor_id = client.post(
            "/game/actor",
            json={"csrf_token": csrf, "campaign_id": campaign_id,
                  "system_id": "dnd5e", "type": "character", "name": "Aria"},
        ).json()["actor_id"]

        modal = client.get(f"/game/actor/sheet/modal/{actor_id}")
        assert modal.status_code == 200
        assert "data-actor-sheet-root" in modal.text
        assert "data-actor-bundle" in modal.text

        bundle = client.get(f"/game/actor/{actor_id}/sheet-bundle")
        assert bundle.status_code == 200
        body = bundle.json()
        assert body["layout"]["kind"] == "actorSheet"
        assert body["actor"]["name"] == "Aria"


def test_content_and_drop_endpoints(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-content-ep@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        actor_id = client.post(
            "/game/actor",
            json={"csrf_token": csrf, "campaign_id": campaign_id,
                  "system_id": "dnd5e", "type": "character", "name": "Aria"},
        ).json()["actor_id"]

        packs = client.get("/game/content/packs/dnd5e")
        assert packs.status_code == 200
        assert any(p["id"] == "dnd5e-weapons" for p in packs.json()["packs"])

        pack = client.get("/game/content/pack/dnd5e/dnd5e-weapons")
        assert pack.status_code == 200
        assert any(e["id"] == "template-longsword" for e in pack.json()["entries"])

        drop = client.post(
            "/game/actor/drop",
            json={"csrf_token": csrf, "actor_id": actor_id,
                  "source": {"kind": "content_pack_entry",
                             "pack_id": "dnd5e-weapons", "entry_id": "template-longsword"},
                  "target": {"drop_zone": "weapons"}},
        )
        assert drop.status_code == 200

        data = client.get(f"/game/actor/{actor_id}/sheet-data").json()["data"]
        assert data["weapons"][0]["name"] == "Espada Longa (modelo)"
        item_id = data["weapons"][0]["id"]

        item_roll = client.post(
            "/game/actor/item/action",
            json={"csrf_token": csrf, "actor_id": actor_id,
                  "item_instance_id": item_id, "action_id": "weapon.damage",
                  "rollOptions": {"extraDice": ["1d4"]}},
        )
        assert item_roll.status_code == 200
        assert item_roll.json()["metadata"]["actionId"] == "weapon.damage"
        assert item_roll.json()["metadata"]["source"] == {
            "kind": "actor_item_instance",
            "itemInstanceId": item_id,
        }
        assert item_roll.json()["metadata"]["formula"]["base"] == "@item.data.damage"
        assert item_roll.json()["metadata"]["rendered"]["chatCard"]["id"] == "weapon-damage"
        assert item_roll.json()["metadata"]["rendered"]["rollToast"]["id"] == "weapon-damage"

        imported = client.post(
            "/game/content/import",
            json={"csrf_token": csrf, "campaign_id": campaign_id,
                  "system_id": "dnd5e", "pack_id": "dnd5e-monsters", "entry_id": "template-monster"},
        )
        assert imported.status_code == 201
        assert imported.json()["actor_id"]
