import time

from app.engine.sdk.semantic_timeline_service import SemanticTimelineService
from app.persistence.repositories.scene_navigation_repository import NavigationRepository
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from tests.conftest import seed_campaign, seed_scene, seed_user


def test_timeline_orders_cues_by_authoritative_offset_and_is_idempotent(db):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);service=SemanticTimelineService()
    definition={"id":"transition","schemaVersion":1,"cues":[{"cueId":"later","offsetMs":100,"type":"NAVIGATION","parameters":{"sceneId":scene["id"],"recipients":{"kind":"self"}}},{"cueId":"now","offsetMs":0,"type":"NAVIGATION","parameters":{"sceneId":scene["id"],"recipients":{"kind":"self"}}}]}
    assert service.register(campaign_id=campaign,package_id="art",definition=definition).success
    started_ms=int(time.time()*1000)
    first=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"transition","idempotencyKey":"storm","startedAt":started_ms}).value
    assert first["executedCueIds"]==["now"] and first["status"]=="RUNNING"
    finished=service.recover_campaign(campaign,started_ms+101)[0]
    assert finished["status"]=="COMPLETED" and finished["executedCueIds"]==["now","later"]
    same=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"transition","idempotencyKey":"storm"}).value
    assert same["id"]==first["id"] and NavigationRepository().get(campaign,gm)["scene_id"]==scene["id"]


def test_timeline_rejects_raw_renderer_and_unbounded_duration(db):
    gm=seed_user();campaign=seed_campaign(gm);service=SemanticTimelineService()
    bad=service.register(campaign_id=campaign,package_id="art",definition={"id":"bad","schemaVersion":1,"cues":[{"offsetMs":0,"type":"RAW_GLSL","parameters":{"source":"void main(){}"}}]})
    huge=service.register(campaign_id=campaign,package_id="art",definition={"id":"huge","schemaVersion":1,"cues":[{"cueId":"huge","offsetMs":600001,"type":"NAVIGATION","parameters":{}}]})
    assert not bad.success and not huge.success
    duplicate=service.register(campaign_id=campaign,package_id="art",definition={"id":"duplicate","schemaVersion":1,"cues":[{"cueId":"same","offsetMs":0,"type":"NAVIGATION","parameters":{}},{"cueId":"same","offsetMs":1,"type":"NAVIGATION","parameters":{}}]})
    assert not duplicate.success


def test_artistic_timeline_composes_first_class_semantic_domains(db,monkeypatch):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);service=SemanticTimelineService()
    monkeypatch.setattr("app.engine.audio.audio_runtime_service.PackageAssetService.resolve",lambda self,pkg,path:(object(),"audio/ogg"))
    cues=[
        {"cueId":"sound","offsetMs":0,"type":"AUDIO_PLAY","parameters":{"asset":{"kind":"package-asset","id":"thunder.ogg"},"channel":"sfx","audience":{"kind":"self"},"idempotencyKey":"ignored"}},
        {"cueId":"title","offsetMs":0,"type":"PRESENTATION_SHOW","parameters":{"mode":"title-card","content":{"title":"Thunder"},"audience":{"kind":"self"},"duration":2}},
        {"cueId":"light","offsetMs":0,"type":"LIGHT_CREATE","parameters":{"sceneId":scene["id"],"x":10,"y":10,"bright_radius":2,"dim_radius":4,"color":"#ffffff","intensity":1}},
        {"cueId":"shader","offsetMs":0,"type":"SHADER_PRESET","parameters":{"sceneId":scene["id"],"presetId":"weather-1","schemaVersion":1,"parameters":{}}},
        {"cueId":"particles","offsetMs":0,"type":"PARTICLE_CREATE","parameters":{"sceneId":scene["id"],"x":10,"y":10,"kind":"rain","scale":2,"density":.5}},
        {"cueId":"navigation","offsetMs":0,"type":"NAVIGATION","parameters":{"sceneId":scene["id"],"recipients":{"kind":"self"}}},
    ]
    assert service.register(campaign_id=campaign,package_id="art",definition={"id":"thunder","schemaVersion":1,"cues":cues}).success
    result=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"thunder","sceneId":scene["id"],"idempotencyKey":"thunder-1"})
    assert result.success and result.value["status"]=="COMPLETED"
    assert result.value["executedCueIds"]==["sound","title","light","shader","particles","navigation"]
    assert {event["type"] for event in result.value["_cueEvents"]}=={"AUDIO_PLAY","PRESENTATION_SHOW","LIGHT_CREATE","SHADER_PRESET","PARTICLE_CREATE","NAVIGATION"}


def test_timeline_cancel_runs_bounded_cleanup_once(db,monkeypatch):
    from types import SimpleNamespace
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);calls=[]
    def execute(*_args,**kwargs):
        calls.append(kwargs["idempotency_key"]);return SimpleNamespace(success=True,value={"ok":True},error_key=None)
    monkeypatch.setattr("app.engine.sdk.durable_workflow_service.DeclarativeActionService.execute",execute)
    service=SemanticTimelineService();definition={"id":"cleanup","schemaVersion":1,"cues":[{"cueId":"now","offsetMs":0,"type":"ACTION","action":"art:start@1","parameters":{},"cleanupAction":"art:stop@1","cleanupInput":{}},{"cueId":"later","offsetMs":5000,"type":"NAVIGATION","parameters":{"sceneId":scene["id"],"recipients":{"kind":"self"}}}]}
    assert service.register(campaign_id=campaign,package_id="art",definition=definition).success
    active=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"cleanup","idempotencyKey":"cleanup"}).value
    cancelled=service.cancel(campaign_id=campaign,user_id=gm,package_id="art",instance_id=active["id"],expected_version=active["version"])
    assert cancelled.success and cancelled.value["status"]=="CANCELLED"
    assert calls==[f"timeline:{active['id']}:now",f"timeline:{active['id']}:cleanup:now"]


def test_timeline_package_unload_and_scene_delete_are_terminal(db):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);service=SemanticTimelineService()
    definition={"id":"later","schemaVersion":1,"cues":[{"cueId":"later","offsetMs":5000,"type":"NAVIGATION","parameters":{"sceneId":scene["id"],"recipients":{"kind":"self"}}}]}
    service.register(campaign_id=campaign,package_id="art",definition=definition)
    one=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"later","sceneId":scene["id"],"idempotencyKey":"one"}).value
    two=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"later","sceneId":scene["id"],"idempotencyKey":"two"}).value
    scene_closed=SemanticInstanceRepository().fail_closed_scene(campaign,scene["id"])
    assert {row["id"] for row in scene_closed}=={one["id"],two["id"]}
    assert all(row["payload"]["completionReason"]=="scene-deleted" for row in scene_closed)
    three=service.start(campaign_id=campaign,user_id=gm,package_id="art",values={"definitionId":"later","idempotencyKey":"three"}).value
    package_closed=SemanticInstanceRepository().fail_closed_package(campaign,"art")
    assert package_closed[0]["id"]==three["id"] and package_closed[0]["payload"]["completionReason"]=="package-unload"
