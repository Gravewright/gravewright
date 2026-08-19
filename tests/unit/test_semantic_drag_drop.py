from app.engine.sdk.semantic_drag_drop_service import SemanticDragDropService
from tests.conftest import seed_campaign, seed_user
from tests.conftest import seed_scene
from app.engine.scenes.scene_object_service import SceneObjectService
from app.engine.sdk.content_reference_service import ContentReference
from app.engine.rules.declarative_action_service import DeclarativeActionResult
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository


def test_registries_are_typed_and_provider_bound(db):
    user=seed_user();campaign=seed_campaign(user);service=SemanticDragDropService()
    source=service.register(campaign_id=campaign,package_id="cards",kind="source",definition={"id":"hand-card","referenceKinds":["card"],"operations":["place"],"schemaVersion":1})
    target=service.register(campaign_id=campaign,package_id="cards",kind="target",definition={"id":"table","surface":"board-zone","targetKinds":["scene-object"],"worldObjectTypeId":"cards.board-zone","operations":["place"],"actionReference":"cards:place@1","schemaVersion":1})
    assert source.success and target.success and len(service.list(campaign_id=campaign,package_id="cards",kind="target").value)==1
    assert not service.register(campaign_id=campaign,package_id="cards",kind="target",definition={"id":"evil","surface":"board-zone","targetKinds":["scene-object"],"operations":["place"],"actionReference":"other:place@1","schemaVersion":1}).success
    assert service.unregister(campaign_id=campaign,package_id="cards",kind="target",entry_id="table").success

def test_concrete_world_target_is_hit_tested_versioned_and_revalidated(db,monkeypatch):
    user=seed_user();campaign=seed_campaign(user);scene=seed_scene(campaign);objects=SceneObjectService();service=SemanticDragDropService()
    objects.register_type(campaign_id=campaign,user_id=user,package_id="cards",definition={"typeId":"cards.board-zone","schemaVersion":1,"displayName":"Zone","dataSchema":{"type":"object"},"geometryKinds":["rect"],"visualDefinition":[],"interactionDefinitions":[]})
    zone=objects.create(campaign_id=campaign,scene_id=scene["id"],user_id=user,package_id="cards",values={"typeId":"cards.board-zone","geometry":{"kind":"rect","x":10,"y":20,"width":100,"height":80}}).value
    service.register(campaign_id=campaign,package_id="cards",kind="source",definition={"id":"card-source","referenceKinds":["card"],"operations":["place"],"schemaVersion":1})
    service.register(campaign_id=campaign,package_id="cards",kind="target",definition={"id":"zone-target","surface":"board-zone","targetKinds":["scene-object"],"worldObjectTypeId":"cards.board-zone","operations":["place"],"actionReference":"cards:place@1","schemaVersion":1})
    monkeypatch.setattr("app.engine.sdk.semantic_drag_drop_service.ContentReferenceService.resolve",lambda *a,**k:{"ref":ContentReference(campaign,"card","card-1").public(),"value":{"id":"card-1"}})
    captured={}
    def execute(*args,**kwargs):captured.update(kwargs);return DeclarativeActionResult(True,{"ok":True})
    monkeypatch.setattr("app.engine.sdk.semantic_drag_drop_service.DeclarativeActionService.execute",execute)
    base={"payload":{"kind":"card-source","reference":"grave://ignored","schemaVersion":1},"operation":"place","idempotencyKey":"once","destination":{"targetDefinitionId":"zone-target","kind":"scene-object","resource":{"id":zone["id"]},"expectedVersion":zone["version"],"worldPosition":{"x":30,"y":30}}}
    result=service.drop(campaign_id=campaign,user_id=user,package_id="cards",values=base)
    assert result.success and captured["drop_context"]["destination"]["resource"]["id"]==zone["id"]
    assert service.drop(campaign_id=campaign,user_id=user,package_id="cards",values={**base,"destination":{**base["destination"],"expectedVersion":99}}).error_key.endswith("stale_version")
    assert service.drop(campaign_id=campaign,user_id=user,package_id="cards",values={**base,"destination":{**base["destination"],"worldPosition":{"x":500,"y":500}}}).error_key.endswith("source_not_visible")

def test_concrete_actor_target_rejects_a_stale_core_version(db,monkeypatch):
    user=seed_user();campaign=seed_campaign(user);service=SemanticDragDropService()
    actor=ActorRepository().create(campaign_id=campaign,system_id="rules",actor_type="character",name="Target",created_by_user_id=user)
    item=ItemRepository().create(campaign_id=campaign,system_id="rules",item_type="gear",name="Source",created_by_user_id=user)
    service.register(campaign_id=campaign,package_id="items",kind="source",definition={"id":"item-source","referenceKinds":["item"],"operations":["copy"],"schemaVersion":1})
    service.register(campaign_id=campaign,package_id="items",kind="target",definition={"id":"actor-target","surface":"core-resource","targetKinds":["actor"],"operations":["copy"],"actionReference":"items:insert@1","schemaVersion":1})
    monkeypatch.setattr("app.engine.sdk.semantic_drag_drop_service.DeclarativeActionService.execute",lambda *a,**k:DeclarativeActionResult(True,{"ok":True}))
    values={"payload":{"kind":"item-source","reference":ContentReference(campaign,"item",item).uri,"schemaVersion":1},"operation":"copy","destination":{"targetDefinitionId":"actor-target","kind":"actor","resource":{"id":actor},"expectedVersion":1}}
    assert service.drop(campaign_id=campaign,user_id=user,package_id="items",values=values).success
    stale={**values,"destination":{**values["destination"],"expectedVersion":99}}
    assert service.drop(campaign_id=campaign,user_id=user,package_id="items",values=stale).error_key=="sdk.ui.dragDrop.stale_version"
