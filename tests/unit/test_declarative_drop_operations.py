from app.engine.decks.card_service import CardService
from app.engine.decks.cards import DrawDestination
from app.engine.rules.declarative_action_registry import RegisteredAction, _validate_definition, ActionContractError
from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.sdk.runtime_authority import RuntimeAuthorityResult
from app.persistence.repositories.card_repository import CardRepository
from tests.conftest import seed_campaign,seed_scene,seed_user
from app.engine.scenes.scene_object_service import SceneObjectService
from app.engine.sheets.actor_item_copy_service import ItemCopyResult
import pytest

def action(op,capability="cards.manage"):
    return RegisteredAction("drop-kit","drop",1,{"type":"object","properties":{}},(capability,),(op,),"REQUIRES_IDEMPOTENCY_KEY",{"maxSteps":16})

def test_card_placement_operation_reuses_cards_and_is_idempotent(db,monkeypatch):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);cards=CardService()
    definition=cards.create_deck_definition(campaign_id=campaign,user_id=gm,name="Drop Deck",description=None,cards=[{"name":"Secret","front_asset_id":"front","quantity":1}]).payload["deck"]
    deck=cards.instantiate_deck(campaign_id=campaign,user_id=gm,deck_definition_id=definition["id"]).payload["deck"]
    drawn=cards.draw(campaign_id=campaign,user_id=gm,deck_instance_id=deck["id"],count=1,destination=DrawDestination.HAND);card=drawn.payload["cards"][0]
    registered=action({"op":"cards.placement.place","card":"SOURCE_CARD","boardZone":"TARGET_SCENE_OBJECT","position":"DROP_WORLD_POSITION"})
    monkeypatch.setattr("app.engine.rules.declarative_action_service.DeclarativeActionRegistry.get",lambda *a,**k:registered)
    monkeypatch.setattr("app.engine.rules.declarative_action_service.SdkRuntimeAuthority.authorize",lambda *a,**k:RuntimeAuthorityResult(True))
    context={"source":{"ref":{"kind":"card","id":card["id"]}},"destination":{"resource":{"id":"zone","sceneId":scene["id"]},"worldPosition":{"x":42,"y":55}}}
    first=DeclarativeActionService().execute(campaign_id=campaign,user_id=gm,package_id="drop-kit",action_id="drop",version=1,inputs={},idempotency_key="once",drop_context=context)
    again=DeclarativeActionService().execute(campaign_id=campaign,user_id=gm,package_id="drop-kit",action_id="drop",version=1,inputs={},idempotency_key="once",drop_context=context)
    assert first.success and again.success and first.value==again.value
    placement=CardRepository().get_scene_card_placement(first.value["changedResources"][0]["id"])
    assert placement["scene_id"]==scene["id"] and placement["face_state"]=="face_down"

def test_catalog_accepts_only_exact_typed_bindings():
    base={"id":"drop","version":1,"inputs":{"type":"object","properties":{}},"idempotency":"REQUIRES_IDEMPOTENCY_KEY"}
    card={**base,"operations":[{"op":"cards.placement.place","card":"SOURCE_CARD","boardZone":"TARGET_SCENE_OBJECT","position":"DROP_WORLD_POSITION"}]}
    assert _validate_definition("kit",card,{"cards.manage"}).required_capabilities==("cards.manage",)
    with pytest.raises(ActionContractError):_validate_definition("kit",{**card,"operations":[{**card["operations"][0],"card":"$input.card"}]},{"cards.manage"})
    with pytest.raises(ActionContractError):_validate_definition("kit",{**base,"operations":[{"op":"resource.invoke","method":"anything"}]},{"cards.manage"})

def test_scene_pin_operation_creates_schema_validated_content_reference(db,monkeypatch):
    gm=seed_user();campaign=seed_campaign(gm);scene=seed_scene(campaign);objects=SceneObjectService()
    objects.register_type(campaign_id=campaign,user_id=gm,package_id="drop-kit",definition={"typeId":"drop-kit.scene-pin","schemaVersion":1,"displayName":"Pin","geometryKinds":["point"],"dataSchema":{"type":"object","properties":{"linkedContent":{"type":"object","format":"content-reference"}},"required":["linkedContent"],"additionalProperties":False},"visualDefinition":[],"interactionDefinitions":[]})
    registered=action({"op":"scene.objects.create","scene":"TARGET_SCENE","position":"DROP_WORLD_POSITION","content":"SOURCE_CONTENT_REFERENCE","objectTypeId":"drop-kit.scene-pin","audience":{"kind":"campaign"}},"scene.objects.write")
    monkeypatch.setattr("app.engine.rules.declarative_action_service.DeclarativeActionRegistry.get",lambda *a,**k:registered)
    monkeypatch.setattr("app.engine.rules.declarative_action_service.SdkRuntimeAuthority.authorize",lambda *a,**k:RuntimeAuthorityResult(True))
    context={"source":{"ref":{"kind":"journal","id":"journal-1","campaignId":campaign}},"destination":{"resource":{"id":scene["id"],"sceneId":scene["id"]},"worldPosition":{"x":12,"y":18}}}
    result=DeclarativeActionService().execute(campaign_id=campaign,user_id=gm,package_id="drop-kit",action_id="drop",version=1,inputs={},idempotency_key="pin",drop_context=context)
    assert result.success
    pin=objects.get(campaign_id=campaign,object_id=result.value["changedResources"][0]["id"],user_id=gm).value
    assert pin["geometry"]=={"kind":"point","x":12.0,"y":18.0} and pin["data"]["linkedContent"]["kind"]=="journal"

def test_actor_item_operation_delegates_only_typed_ids_and_fixed_slot(db,monkeypatch):
    registered=action({"op":"actors.items.insertCopy","item":"SOURCE_ITEM","actor":"TARGET_ACTOR","slot":"inventory"},"actors.items.write")
    monkeypatch.setattr("app.engine.rules.declarative_action_service.DeclarativeActionRegistry.get",lambda *a,**k:registered)
    monkeypatch.setattr("app.engine.rules.declarative_action_service.SdkRuntimeAuthority.authorize",lambda *a,**k:RuntimeAuthorityResult(True))
    captured={}
    def insert(self,**kwargs):captured.update(kwargs);return ItemCopyResult(True,{"copy":{"id":"local"},"actorId":kwargs["actor_id"],"slot":kwargs["slot_id"],"version":2})
    monkeypatch.setattr("app.engine.rules.declarative_action_service.ActorItemCopyService.insert",insert)
    context={"source":{"ref":{"kind":"item","id":"item-1"}},"destination":{"resource":{"id":"actor-1"}}}
    result=DeclarativeActionService().execute(campaign_id="campaign",user_id="user",package_id="drop-kit",action_id="drop",version=1,inputs={},idempotency_key="copy",drop_context=context)
    assert result.success and captured=={"campaign_id":"campaign","actor_id":"actor-1","source_item_id":"item-1","slot_id":"inventory","user_id":"user"}
