from app.engine.sdk.scene_navigation_service import SceneNavigationService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_persistent_self_and_gm_directed_navigation_without_token_mutation(db):
    gm=seed_user();player=seed_user();campaign=seed_campaign(gm);seed_member(campaign,player,"player");a=seed_scene(campaign);b=seed_scene(campaign)
    service=SceneNavigationService(); directed=service.go(campaign_id=campaign,user_id=gm,values={"sceneId":b["id"],"recipients":{"kind":"users","ids":[player]},"idempotencyKey":"portal"})
    assert directed.success and service.get(campaign_id=campaign,user_id=player).value["sceneId"]==b["id"]
    assert service.go(campaign_id=campaign,user_id=player,values={"sceneId":a["id"],"recipients":{"kind":"users","ids":[gm]}}).error_key=="sdk.navigation.not_authorized"
