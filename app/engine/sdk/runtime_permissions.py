"""Semantic permission decisions exposed by ``sdk.permissions.can``."""

from __future__ import annotations

from app.business.permissions.permission_service import PermissionService
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.items.item_permissions import can_edit_item, can_view_item
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.token_repository import TokenRepository
from app.domain.permissions.permissions import TablePermission


class SdkRuntimePermissionInspector:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.actors = ActorRepository()
        self.items = ItemRepository()
        self.tokens = TokenRepository()
        self.table = PermissionService()

    def can(self, *, action: str, campaign_id: str, user_id: str, resource_id: str = "") -> tuple[bool, bool]:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return True, False
        context = dict(campaign)
        if action in {"actor.read", "actor.update", "actor.delete"}:
            actor = self.actors.get(resource_id)
            if not actor or actor["campaign_id"] != campaign_id or actor["status"] != "active":
                return True, False
            check = can_view_actor if action == "actor.read" else can_edit_actor
            return True, check(actor=actor, campaign=context, user_id=user_id)
        if action in {"item.read", "item.update", "item.delete"}:
            item = self.items.get(resource_id)
            if not item or item["campaign_id"] != campaign_id or item["status"] != "active":
                return True, False
            check = can_view_item if action == "item.read" else can_edit_item
            return True, check(item=item, campaign=context, user_id=user_id)
        if action == "token.move":
            token = self.tokens.get_by_id(resource_id)
            if not token:
                return True, False
            return True, TokenService().can_control_token(token=token, user_id=user_id, campaign_id=campaign_id)
        if action in {"scene.geometry.update", "walls.manage", "lighting.manage", "scene.effects.update", "effects.manage", "combat.manage"}:
            return True, context.get("member_role") == "gm"
        if action == "fog.manage":
            return True, self.table.can(
                user_id=user_id, campaign_id=campaign_id, permission=TablePermission.FOG_PAINT
            )
        if action == "cards.manage":
            return True, context.get("member_role") in {"gm", "assistant_gm"}
        if action == "tools.register":
            return True, True
        if action == "templates.manage":
            return True, self.table.can(
                user_id=user_id, campaign_id=campaign_id, permission=TablePermission.BOARD_MARKER_CREATE
            )
        permission = {
            "scene.read": "scene.view", "combat.read": "combat.view", "chat.read": "chat.view",
        }.get(action, action)
        from app.domain.permissions.groups import ALL_CORE_PERMISSION_KEYS
        if permission not in ALL_CORE_PERMISSION_KEYS:
            return False, False
        return True, self.table.can(user_id=user_id, campaign_id=campaign_id, permission=permission)
