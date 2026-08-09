from litestar.testing import TestClient
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user

def test_gm_wall_http_flow_and_player_read(db):
    from main import app
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        made=client.post("/game/walls",json={"campaign_id":campaign,"scene_id":scene["id"],"kind":"door","x1":0,"y1":0,"x2":70,"y2":0})
        toggled=client.post("/game/walls/door-state",json={"campaign_id":campaign,"wall_id":made.json()["wall"]["id"],"door_state":"locked"})
        login(client,player)
        state=client.get(f'/game/walls/{scene["id"]}',params={"campaign_id":campaign})
        denied=client.post("/game/walls/delete",json={"campaign_id":campaign,"wall_id":made.json()["wall"]["id"]})
    assert made.status_code==201 and toggled.json()["wall"]["door_state"]=="locked"
    assert state.status_code==200 and len(state.json()["walls"])==1
    assert denied.status_code==403

def test_players_operate_doors_over_http_but_locking_is_gm_only(db):
    from main import app
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        door=client.post("/game/walls",json={"campaign_id":campaign,"scene_id":scene["id"],"kind":"door","x1":0,"y1":0,"x2":70,"y2":0}).json()["wall"]["id"]
        login(client,player)
        opened=client.post("/game/walls/door-state",json={"campaign_id":campaign,"wall_id":door,"door_state":"open"})
        refused=client.post("/game/walls/door-state",json={"campaign_id":campaign,"wall_id":door,"door_state":"locked"})
        login(client,gm)
        client.post("/game/walls/door-state",json={"campaign_id":campaign,"wall_id":door,"door_state":"locked"})
        login(client,player)
        blocked=client.post("/game/walls/door-state",json={"campaign_id":campaign,"wall_id":door,"door_state":"open"})
    assert opened.status_code==200 and opened.json()["wall"]["door_state"]=="open"
    assert refused.status_code==403 and refused.json()["error_key"]=="lighting.errors.locked"
    assert blocked.status_code==403

def test_light_endpoints_round_trip(db):
    from main import app
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        made=client.post("/game/lights",json={"campaign_id":campaign,"scene_id":scene["id"],"x":40,"y":60,"animation":"pulse"})
        light=made.json()["light"]["id"]
        moved=client.post("/game/lights/update",json={"campaign_id":campaign,"light_id":light,"x":90,"y":95})
        login(client,player)
        listed=client.get(f'/game/lights/{scene["id"]}',params={"campaign_id":campaign})
        denied=client.post("/game/lights/delete",json={"campaign_id":campaign,"light_id":light})
    assert made.status_code==201 and made.json()["light"]["animation"]=="pulse"
    assert moved.status_code==200 and (moved.json()["light"]["x"],moved.json()["light"]["y"])==(90,95)
    assert listed.status_code==200 and len(listed.json()["lights"])==1
    assert denied.status_code==403

def test_move_node_endpoint_drags_welded_walls(db):
    from main import app
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,gm)
        first=client.post("/game/walls",json={"campaign_id":campaign,"scene_id":scene["id"],"kind":"wall","x1":0,"y1":0,"x2":70,"y2":0}).json()["wall"]["id"]
        second=client.post("/game/walls",json={"campaign_id":campaign,"scene_id":scene["id"],"kind":"wall","x1":70,"y1":0,"x2":70,"y2":70}).json()["wall"]["id"]
        moved=client.post("/game/walls/move-node",json={"campaign_id":campaign,"scene_id":scene["id"],"from_x":70,"from_y":0,"to_x":95,"to_y":33})
        login(client,player)
        denied=client.post("/game/walls/move-node",json={"campaign_id":campaign,"scene_id":scene["id"],"from_x":95,"from_y":33,"to_x":10,"to_y":10})
    assert moved.status_code==200
    walls={wall["id"]: wall for wall in moved.json()["walls"]}
    assert (walls[first]["x2"],walls[first]["y2"])==(95,33)
    assert (walls[second]["x1"],walls[second]["y1"])==(95,33)
    assert denied.status_code==403
