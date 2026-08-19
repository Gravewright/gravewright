import time
from app.engine.sdk.semantic_presentation_service import SemanticPresentationService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user
from app.engine.scenes.scene_object_service import SceneObjectService
from app.persistence.repositories.token_repository import TokenRepository

def world():
    gm=seed_user();player=seed_user();other=seed_user();campaign=seed_campaign(gm);seed_member(campaign,player,"player");seed_member(campaign,other,"player");scene=seed_scene(campaign)
    return gm,player,other,campaign,scene["id"]

def test_remote_show_projection_update_close_and_recipient_filter(db):
    gm,player,other,campaign,scene=world();service=SemanticPresentationService()
    made=service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"title-card","sceneId":scene,"content":{"title":"THE CRYPT","subtitle":"Below"},"audience":{"kind":"users","ids":[player]},"duration":60})
    assert made.success and made.value["version"]==1
    assert service.list(campaign_id=campaign,user_id=player,package_id="cinema",scene_id=scene).value[0]["id"]==made.value["id"]
    assert service.list(campaign_id=campaign,user_id=other,package_id="cinema",scene_id=scene).value==[]
    changed=service.update(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"],patch={"content":{"title":"THE VAULT"}},expected_version=1)
    assert changed.success and changed.value["version"]==2
    assert service.update(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"],patch={"content":{"title":"stale"}},expected_version=1).error_key.endswith("stale_version")
    assert service.close(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"],expected_version=2).success
    assert service.close(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"]).success

def test_modes_countdown_security_and_remote_authority(db):
    gm,player,_,campaign,scene=world();service=SemanticPresentationService()
    for mode in ("screen-overlay","title-card","fade","countdown"):
        values={"mode":mode,"sceneId":scene,"content":{"title":"Safe"},"duration":30,"audience":{"kind":"self"}}
        if mode=="countdown":values["deadline"]=int(time.time())+30
        assert service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values=values).success
    assert not service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"title-card","content":{"title":"<script>"},"audience":{"kind":"self"}}).success
    assert service.show(campaign_id=campaign,user_id=player,package_id="cinema",values={"mode":"title-card","content":{"title":"spam"},"audience":{"kind":"users","ids":[gm]}}).error_key.endswith("not_authorized")

def test_token_and_world_object_anchors_fail_closed_for_hidden_resources(db):
    gm,player,_,campaign,scene=world();service=SemanticPresentationService()
    token=TokenRepository().create(scene_id=scene,actor_id=None,grid_x=1,grid_y=1,controlled_by_role="gm")
    hud=service.show(campaign_id=campaign,user_id=gm,package_id="hud",values={"mode":"world-anchor","anchor":{"kind":"token","id":token["id"],"sceneId":scene},"content":{"title":"HP"},"audience":{"kind":"users","ids":[player]},"duration":30})
    assert hud.success and service.list(campaign_id=campaign,user_id=player,package_id="hud",scene_id=scene).value
    objects=SceneObjectService();definition={"typeId":"hud.marker","schemaVersion":1,"displayName":"Marker","dataSchema":{"type":"object"},"geometryKinds":["point"],"visualDefinition":[{"kind":"icon"}],"interactionDefinitions":[]}
    objects.register_type(campaign_id=campaign,user_id=gm,package_id="hud",definition=definition)
    hidden=objects.create(campaign_id=campaign,scene_id=scene,user_id=gm,package_id="hud",values={"typeId":"hud.marker","geometry":{"kind":"point","x":10,"y":10},"audience":{"kind":"gm"}}).value
    anchored=service.show(campaign_id=campaign,user_id=gm,package_id="hud",values={"mode":"world-anchor","anchor":{"kind":"scene-object","id":hidden["id"]},"content":{"title":"Secret"},"audience":{"kind":"users","ids":[player]},"duration":30})
    assert anchored.success
    visible=service.list(campaign_id=campaign,user_id=player,package_id="hud",scene_id=scene).value
    assert all(item["id"]!=anchored.value["id"] for item in visible)

def test_authoritative_server_time_completion_and_bounded_policy(db,monkeypatch):
    gm,player,_,campaign,scene=world();service=SemanticPresentationService();now=time.time()
    made=service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"fade","sceneId":scene,"content":{"value":1},"audience":{"kind":"users","ids":[player]},"duration":1,"completion":{"policy":"server-time","timeoutMs":500}})
    assert made.success and made.value["status"]=="active" and made.value["endsAt"]>made.value["startedAt"]
    monkeypatch.setattr("app.engine.sdk.semantic_presentation_service.time.time",lambda:now+2)
    done=service.get(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"])
    assert done.success and done.value["status"]=="completed" and done.value["completionReason"]=="server-time"
    assert not service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"fade","audience":{"kind":"self"},"completion":{"policy":"server-time","timeoutMs":-1}}).success

def test_recipient_ack_is_authenticated_idempotent_and_private(db,monkeypatch):
    gm,player,other,campaign,scene=world();service=SemanticPresentationService();now=time.time()
    made=service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"title-card","sceneId":scene,"content":{"title":"Ready"},"audience":{"kind":"users","ids":[player]},"duration":1,"completion":{"policy":"all-connected-recipients","timeoutMs":5000}})
    assert not service.acknowledge(campaign_id=campaign,user_id=other,package_id="cinema",presentation_id=made.value["id"]).success
    assert service.acknowledge(campaign_id=campaign,user_id=player,package_id="cinema",presentation_id=made.value["id"]).error_key=="sdk.ui.presentations.not_complete"
    monkeypatch.setattr("app.engine.sdk.semantic_presentation_service.time.time",lambda:now+2)
    first=service.acknowledge(campaign_id=campaign,user_id=player,package_id="cinema",presentation_id=made.value["id"])
    second=service.acknowledge(campaign_id=campaign,user_id=player,package_id="cinema",presentation_id=made.value["id"])
    assert first.success and second.success and "acknowledgedRecipients" not in second.value
    monkeypatch.setattr("app.engine.sdk.semantic_presentation_service.PresenceService.list_online_user_ids",lambda self,ids:{player})
    done=service.get(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"])
    assert done.value["status"]=="completed" and done.value["completionReason"]=="recipients" and done.value["recipientSummary"]=={"expected":1,"completed":1}

def test_package_unload_retains_typed_terminal_for_active_observers(db):
    gm,player,_,campaign,scene=world();service=SemanticPresentationService()
    made=service.show(campaign_id=campaign,user_id=gm,package_id="cinema",values={"mode":"fade","sceneId":scene,"content":{"value":1},"audience":{"kind":"users","ids":[player]},"duration":60})
    cancelled=service.close_package(campaign_id=campaign,package_id="cinema")
    assert len(cancelled)==1 and cancelled[0]["id"]==made.value["id"] and cancelled[0]["status"]=="cancelled" and cancelled[0]["completionReason"]=="package-unload"
    observed=service.get(campaign_id=campaign,user_id=gm,package_id="cinema",presentation_id=made.value["id"])
    assert observed.success and observed.value["status"]=="cancelled"
