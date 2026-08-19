import json, time
from app.persistence.repositories.scene_zone_repository import SceneZoneRepository
from tests.conftest import seed_campaign, seed_scene, seed_user

def test_zone_candidate_lookup_scales_by_bounds_not_global_membership(db):
    gm=seed_user(); campaign=seed_campaign(gm); scene=seed_scene(campaign)["id"]; repo=SceneZoneRepository()
    for index in range(1000):
        x=float(index*100)
        repo.create(scene_id=scene,zone_type="benchmark",geometry_json=json.dumps({"shape":"rect","x":x,"y":0,"width":10,"height":10}),vertical_bottom=None,vertical_top=None,audience_json='{"kind":"gm"}',enabled=1,tags_json="[]",package_id="benchmark",provider_id=None,min_x=x,min_y=0,max_x=x+10,max_y=10)
    started=time.perf_counter()
    for _ in range(100):
        candidates=repo.candidates(scene,49_995,-1,50_015,11)
        assert len(candidates)<=2
    elapsed=time.perf_counter()-started
    assert elapsed<1.0
