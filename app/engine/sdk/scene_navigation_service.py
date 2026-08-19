"""Scene navigation: changing what a user is looking at.

Navigation moves a viewpoint and nothing else. It never moves a token, and a
package may only navigate users it is authorized to address.
"""

from __future__ import annotations

from app.engine.scenes.scene_service import SceneService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_navigation_repository import NavigationRepository
from app.persistence.repositories.scene_repository import SceneRepository

from app.engine.sdk.semantic_authority import SemanticResult

class SceneNavigationService:
    def __init__(self):self.repo=NavigationRepository()
    def go(self,*,campaign_id,user_id,values):
        try:
            scene=SceneRepository().get_by_id(str(values.get("sceneId") or ""))
            if not scene or scene.get("campaign_id")!=campaign_id:raise LookupError
            members=CampaignRepository().list_members(campaign_id=campaign_id);member_ids={m["user_id"] for m in members};role=CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
            recipients=values.get("recipients",{"kind":"self"});kind=recipients.get("kind") if isinstance(recipients,dict) else None
            ids=[user_id] if kind=="self" else ([m["user_id"] for m in members if m.get("role") in {"gm","assistant_gm"}] if kind=="gm" else (list(member_ids) if kind=="campaign" else list(dict.fromkeys(recipients.get("ids",[]))) if kind=="users" else []))
            if not ids or len(ids)>64 or any(i not in member_ids for i in ids) or (set(ids)!={user_id} and role not in {"gm","assistant_gm"}):raise PermissionError
            if any(not SceneService().assert_user_can_view_scene(scene=scene,user_id=recipient) for recipient in ids):raise PermissionError
            rows=[self.repo.set(campaign_id,recipient,scene["id"],str(values.get("reason") or "")[:512],values.get("idempotencyKey")) for recipient in ids]
            return SemanticResult(True,{"sceneId":scene["id"],"recipientIds":ids,"states":[self._public(r) for r in rows]})
        except LookupError:return SemanticResult(False,error_key="sdk.navigation.scene_not_found")
        except (TypeError,ValueError,PermissionError):return SemanticResult(False,error_key="sdk.navigation.not_authorized")
    def get(self,*,campaign_id,user_id):
        row=self.repo.get(campaign_id,user_id);return SemanticResult(True,self._public(row) if row else None)
    @staticmethod
    def _public(row):return {"campaignId":row["campaign_id"],"userId":row["user_id"],"sceneId":row["scene_id"],"reason":row["reason"],"version":row["version"],"updatedAt":row["updated_at"]}
