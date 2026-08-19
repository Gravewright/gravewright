import json,time,uuid
import pytest
from sqlalchemy import insert
from app.engine.scenes.scene_object_service import SceneObjectService
from app.persistence.database import engine_begin
from app.persistence.tables import scene_objects
from tests.conftest import seed_campaign,seed_scene,seed_user

@pytest.mark.parametrize("count",[10,100,1000,5000])
def test_scene_object_candidate_lookup_is_spatially_bounded(db,count):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign)["id"];now=int(time.time())
    rows=[]
    for index in range(count):
        x=float(index*50);rows.append({"id":uuid.uuid4().hex,"scene_id":scene,"type_id":"bench.point","provider_package_id":"bench","schema_version":1,"geometry_json":json.dumps({"kind":"point","x":x,"y":x}),"transform_json":"{\"rotation\":0,\"scale\":1}","presentation_json":"{}","data_json":"{}","audience_json":"{\"kind\":\"campaign\"}","enabled":1,"min_x":x-12,"min_y":x-12,"max_x":x+12,"max_y":x+12,"search_text":"","version":1,"created_at":now,"updated_at":now})
    with engine_begin() as conn:conn.execute(insert(scene_objects),rows)
    started=time.perf_counter();hits=SceneObjectService().repo.candidates(scene,0,0,8);elapsed=time.perf_counter()-started
    assert len(hits)<=1 and elapsed<0.25
