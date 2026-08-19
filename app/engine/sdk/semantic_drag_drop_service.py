"""Semantic drag and drop: typed pointer gestures resolved by the server.

A drop states what was carried and where it landed, as content references and
a world position. Core re-resolves both against current authority and hands the
result to a registered action, so a gesture can never assert an outcome the
user could not have performed directly.
"""

from __future__ import annotations

from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.scenes.scene_object_service import SceneObjectService
from app.engine.scenes.scene_service import SceneService
from app.engine.sdk.content_reference_service import ContentReferenceService
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.semantic_registration_repository import SemanticRegistrationRepository

from app.engine.sdk.semantic_authority import ACTION_REFERENCE, IDENTIFIER, SemanticResult

class SemanticDragDropService:
    OPS={"move","copy","link","attach","place"}; REGISTRIES={"source":"drag-source","target":"drop-target"}
    def __init__(self):self.repo=SemanticRegistrationRepository()
    def register(self,*,campaign_id,package_id,kind,definition):
        try:
            entry=str(definition.get("id") or "");ops=definition.get("operations",[])
            if kind not in self.REGISTRIES or not IDENTIFIER.fullmatch(entry) or not isinstance(ops,list) or not ops or len(ops)>5 or any(op not in self.OPS for op in ops):raise ValueError
            allowed={"id","referenceKinds","operations","label","icon","surface","targetKinds","worldObjectTypeId","actionReference","schemaVersion"}
            if set(definition)-allowed or definition.get("schemaVersion",1)!=1:raise ValueError
            if kind=="source" and (not isinstance(definition.get("referenceKinds"),list) or len(definition["referenceKinds"])>16):raise ValueError
            if kind=="target":
                if definition.get("surface") not in {"application-region","scene-world-object","board-zone","core-resource"}:raise ValueError
                target_kinds=definition.get("targetKinds")
                if not isinstance(target_kinds,list) or not target_kinds or not set(target_kinds)<={"actor","scene-object","scene-surface"}:raise ValueError
                match=ACTION_REFERENCE.fullmatch(str(definition.get("actionReference") or ""))
                if not match or match.group(1)!=package_id:raise ValueError
            row=self.repo.put(campaign_id,package_id,self.REGISTRIES[kind],entry,definition)
            return SemanticResult(True,self._public(row))
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.ui.dragDrop.invalid_definition")
    def unregister(self,*,campaign_id,package_id,kind,entry_id):
        if kind not in self.REGISTRIES:return SemanticResult(False,error_key="sdk.ui.dragDrop.invalid_definition")
        self.repo.remove(campaign_id,package_id,self.REGISTRIES[kind],entry_id);return SemanticResult(True,{"id":entry_id,"active":False})
    def list(self,*,campaign_id,package_id,kind):return SemanticResult(True,[self._public(r) for r in self.repo.list(campaign_id,self.REGISTRIES[kind],package_id)])
    def drop(self,*,campaign_id,user_id,package_id,values):
        try:
            if set(values)-{"payload","destination","operation","idempotencyKey"}:raise ValueError
            payload=values.get("payload"); operation=values.get("operation");destination=values.get("destination")
            if not isinstance(payload,dict) or set(payload)-{"kind","reference","sourceContext","metadata","schemaVersion"} or payload.get("schemaVersion")!=1 or operation not in self.OPS:raise ValueError
            if not isinstance(destination,dict) or set(destination)-{"targetDefinitionId","kind","resource","expectedVersion","worldPosition","sceneContext"}:raise ValueError
            target_id=str(destination.get("targetDefinitionId") or "");source=self.repo.get(campaign_id,package_id,"drag-source",str(payload.get("kind") or ""));target=self.repo.get(campaign_id,package_id,"drop-target",target_id)
            if not source or not target or operation not in source["definition"]["operations"] or operation not in target["definition"]["operations"]:raise LookupError
            reference=str(payload.get("reference") or "");resolved=ContentReferenceService().resolve(reference,campaign_id=campaign_id,user_id=user_id)
            if not resolved:raise PermissionError
            ref_kind=str(resolved["ref"].get("kind") or "")
            if ref_kind not in source["definition"]["referenceKinds"]:raise ValueError
            concrete=self._destination(campaign_id,user_id,target["definition"],destination)
            action=ACTION_REFERENCE.fullmatch(target["definition"]["actionReference"])
            context={"source":resolved,"destination":concrete,"operation":operation,"principal":{"userId":user_id},"campaignId":campaign_id,"provenance":{"targetDefinitionId":target_id,"providerPackageId":package_id}}
            result=DeclarativeActionService().execute(campaign_id=campaign_id,user_id=user_id,package_id=action.group(1),action_id=action.group(2),version=int(action.group(3)),inputs={},idempotency_key=values.get("idempotencyKey"),drop_context=context)
            return SemanticResult(result.success,{"operation":operation,"source":resolved,"destination":concrete,"actionResult":result.value} if result.success else None,result.error_key)
        except PermissionError:return SemanticResult(False,error_key="sdk.ui.dragDrop.source_not_visible")
        except RuntimeError:return SemanticResult(False,error_key="sdk.ui.dragDrop.stale_version")
        except LookupError:return SemanticResult(False,error_key="sdk.ui.dragDrop.stale_target")
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.ui.dragDrop.invalid_payload")
    @staticmethod
    def _destination(campaign_id,user_id,definition,value):
        kind=value.get("kind");resource=value.get("resource");expected=value.get("expectedVersion")
        if kind not in definition["targetKinds"] or not isinstance(resource,dict) or set(resource)-{"id","sceneId","typeId"}:raise ValueError
        if kind=="actor":
            resolved=ContentReferenceService().resolve({"kind":"actor","id":resource.get("id"),"campaignId":campaign_id},campaign_id=campaign_id,user_id=user_id)
            if not resolved:raise PermissionError
            actor=resolved.get("value") or {}
            if expected is not None and actor.get("version")!=expected:raise RuntimeError
            concrete={"kind":kind,"resource":{"id":resolved["ref"]["id"]}}
        elif kind=="scene-object":
            found=SceneObjectService().get(campaign_id=campaign_id,object_id=str(resource.get("id") or ""),user_id=user_id)
            if not found.success:raise PermissionError
            obj=found.value
            if definition.get("worldObjectTypeId") and obj["typeId"]!=definition["worldObjectTypeId"]:raise ValueError
            if expected is not None and obj["version"]!=expected:raise RuntimeError
            position=value.get("worldPosition")
            if not isinstance(position,dict) or set(position)!={"x","y"}:raise ValueError
            hits=SceneObjectService().hit_test(campaign_id=campaign_id,scene_id=obj["sceneId"],user_id=user_id,x=position["x"],y=position["y"])
            if not hits.success or not any(hit["id"]==obj["id"] for hit in hits.value):raise PermissionError
            concrete={"kind":kind,"resource":{"id":obj["id"],"sceneId":obj["sceneId"],"typeId":obj["typeId"]},"worldPosition":position,"version":obj["version"]}
        else:
            scene=SceneRepository().get_by_id(str(resource.get("id") or ""))
            if not scene or scene.get("campaign_id")!=campaign_id or not SceneService().assert_user_can_view_scene(scene=scene,user_id=user_id):raise PermissionError
            position=value.get("worldPosition")
            if not isinstance(position,dict) or set(position)!={"x","y"}:raise ValueError
            SceneObjectService.geometry({"kind":"point",**position})
            concrete={"kind":kind,"resource":{"id":scene["id"],"sceneId":scene["id"]},"worldPosition":position}
        return concrete
    @staticmethod
    def _public(row):return {"id":row["entry_id"],"packageId":row["package_id"],**row["definition"]}
