from app.engine.scenes.scene_wall_service import SceneWallService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user

def test_gm_creates_walls_and_moves_doors_through_every_state(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    wall=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=0)
    door=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="door",x1=100,y1=0,x2=200,y2=0)
    assert wall.success and door.success and door.payload["wall"]["door_state"] == "closed"
    door_id=door.payload["wall"]["id"]
    for state in ("open","locked","closed"):
        result=service.set_door_state(campaign_id=campaign,wall_id=door_id,user_id=gm,door_state=state)
        assert result.success and result.payload["wall"]["door_state"] == state
    assert len(service.state(campaign_id=campaign,scene_id=scene["id"],user_id=gm).payload["walls"]) == 2

def test_players_operate_unlocked_doors_but_never_the_lock(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm); seed_member(campaign,player,"player")
    scene=seed_scene(campaign); service=SceneWallService()
    door=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="door",x1=0,y1=0,x2=70,y2=0).payload["wall"]["id"]

    opened=service.set_door_state(campaign_id=campaign,wall_id=door,user_id=player,door_state="open")
    assert opened.success and opened.payload["wall"]["door_state"] == "open", "jogador abre porta destrancada"
    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=player,door_state="closed").success

    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=player,door_state="locked").error_key == "lighting.errors.locked", "jogador nao tranca"
    service.set_door_state(campaign_id=campaign,wall_id=door,user_id=gm,door_state="locked")
    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=player,door_state="open").error_key == "lighting.errors.locked", "trancada nao cede ao jogador"
    assert service.walls.get(door)["door_state"] == "locked"
    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=gm,door_state="closed").success, "GM destranca"

def test_non_members_cannot_touch_doors(db):
    gm=seed_user(name="GM"); stranger=seed_user(name="Stranger"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    door=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="door",x1=0,y1=0,x2=70,y2=0).payload["wall"]["id"]
    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=stranger,door_state="open").error_key == "lighting.errors.denied"

def test_door_state_rejects_unknown_values_and_plain_walls(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    wall=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=0).payload["wall"]["id"]
    door=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="door",x1=100,y1=0,x2=200,y2=0).payload["wall"]["id"]

    assert service.set_door_state(campaign_id=campaign,wall_id=door,user_id=gm,door_state="ajar").error_key == "lighting.errors.invalid"
    assert service.set_door_state(campaign_id=campaign,wall_id=wall,user_id=gm,door_state="open").error_key == "lighting.errors.not_found"
    # o estado invalido nao pode ter vazado para o banco
    assert service.walls.get(door)["door_state"] == "closed"

def test_players_read_but_cannot_mutate_walls(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm); seed_member(campaign,player,"player"); scene=seed_scene(campaign); service=SceneWallService()
    assert service.state(campaign_id=campaign,scene_id=scene["id"],user_id=player).success
    denied=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=player,kind="wall",x1=0,y1=0,x2=10,y2=10)
    assert denied.error_key == "lighting.errors.denied"

def test_moving_a_node_drags_every_wall_welded_to_it(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    make=lambda **kw: service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",**kw).payload["wall"]["id"]
    horizontal=make(x1=0,y1=0,x2=100,y2=0)
    vertical=make(x1=100,y1=0,x2=100,y2=100)
    distant=make(x1=300,y1=300,x2=400,y2=300)

    moved=service.move_node(campaign_id=campaign,scene_id=scene["id"],user_id=gm,from_x=100,from_y=0,to_x=140,to_y=60)
    assert moved.success
    walls={wall["id"]: wall for wall in moved.payload["walls"]}
    a,b,c=walls[horizontal],walls[vertical],walls[distant]
    assert (a["x2"],a["y2"]) == (140,60), "ponta da primeira parede acompanha o no"
    assert (b["x1"],b["y1"]) == (140,60), "ponta soldada da segunda parede acompanha junto"
    assert (a["x1"],a["y1"]) == (0,0) and (b["x2"],b["y2"]) == (100,100), "as outras pontas ficam paradas"
    assert (c["x1"],c["y1"],c["x2"],c["y2"]) == (300,300,400,300), "parede distante nao e tocada"

def test_creating_near_an_existing_node_persists_one_canonical_junction(db):
    gm=seed_user(name="GM");campaign=seed_campaign(gm);scene=seed_scene(campaign);service=SceneWallService()
    first=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=100).payload["wall"]
    second=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=100.7,y1=99.6,x2=200,y2=100).payload["wall"]
    assert (second["x1"],second["y1"])==(first["x2"],first["y2"])==(100,100)
    moved=service.move_node(campaign_id=campaign,scene_id=scene["id"],user_id=gm,from_x=100,from_y=100,to_x=120,to_y=130)
    walls={wall["id"]:wall for wall in moved.payload["walls"]}
    assert (walls[first["id"]]["x2"],walls[first["id"]]["y2"])==(120,130)
    assert (walls[second["id"]]["x1"],walls[second["id"]]["y1"])==(120,130)

def test_move_node_rejects_collapsing_and_non_gm(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player"); campaign=seed_campaign(gm); seed_member(campaign,player,"player")
    scene=seed_scene(campaign); service=SceneWallService()
    service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=0)

    assert service.move_node(campaign_id=campaign,scene_id=scene["id"],user_id=player,from_x=0,from_y=0,to_x=10,to_y=10).error_key == "lighting.errors.denied"
    # arrastar uma ponta para cima da outra degeneraria a parede
    assert service.move_node(campaign_id=campaign,scene_id=scene["id"],user_id=gm,from_x=0,from_y=0,to_x=100,to_y=0).error_key == "lighting.errors.invalid"
    assert service.move_node(campaign_id=campaign,scene_id=scene["id"],user_id=gm,from_x=900,from_y=900,to_x=910,to_y=910).error_key == "lighting.errors.not_found"
    unchanged=service.state(campaign_id=campaign,scene_id=scene["id"],user_id=gm).payload["walls"][0]
    assert (unchanged["x1"],unchanged["y1"],unchanged["x2"],unchanged["y2"]) == (0,0,100,0)

def test_move_endpoint_detaches_only_one_wall_from_a_welded_node(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    first=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=0).payload["wall"]
    second=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=100,y1=0,x2=100,y2=100).payload["wall"]
    moved=service.move_endpoint(campaign_id=campaign,scene_id=scene["id"],wall_id=second["id"],endpoint=1,user_id=gm,to_x=140,to_y=40)
    assert moved.success
    walls={wall["id"]:wall for wall in moved.payload["walls"]}
    assert (walls[first["id"]]["x2"],walls[first["id"]]["y2"]) == (100,0)
    assert (walls[second["id"]]["x1"],walls[second["id"]]["y1"]) == (140,40)

def test_move_many_preserves_ids_and_only_moves_the_selection(db):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign); service=SceneWallService()
    first=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=100,y2=0).payload["wall"]
    second=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=100,y1=0,x2=200,y2=0).payload["wall"]
    result=service.move_many(campaign_id=campaign,scene_id=scene["id"],wall_ids=[first["id"]],user_id=gm,dx=25,dy=50)
    assert result.success
    walls={wall["id"]:wall for wall in result.payload["walls"]}
    assert (walls[first["id"]]["x1"],walls[first["id"]]["y1"],walls[first["id"]]["x2"],walls[first["id"]]["y2"]) == (25,50,125,50)
    assert (walls[second["id"]]["x1"],walls[second["id"]]["y1"]) == (100,0)

def test_invalid_and_cross_campaign_walls_are_rejected(db):
    gm=seed_user(name="GM"); other=seed_user(name="Other"); campaign=seed_campaign(gm); other_campaign=seed_campaign(other); scene=seed_scene(other_campaign); service=SceneWallService()
    assert not service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=20,y2=20).success
    own_scene=seed_scene(campaign)
    assert service.create(campaign_id=campaign,scene_id=own_scene["id"],user_id=gm,kind="wall",x1=0,y1=0,x2=0,y2=0).error_key == "lighting.errors.invalid"
