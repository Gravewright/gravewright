"""Item visibility/edit rules (Gravewright SDK — mirrors actor permissions).

GM sees and edits everything. Otherwise access is granted by ownership
(``item_owners``) or an explicit per-user grant (``item_permissions``).
The ``permissions_json`` column is not consulted (kept for parity/back-compat).
"""

from __future__ import annotations

from app.domain.roles import has_full_view
from app.persistence.repositories.item_permission_repository import ItemPermissionRepository
from app.persistence.repositories.item_repository import ItemRepository


def _is_gm(campaign: dict) -> bool:
    return campaign.get("member_role") == "gm"


def can_view_item(*, item: dict, campaign: dict, user_id: str) -> bool:
                                                                     
    if has_full_view(campaign.get("member_role")):
        return True
    if ItemRepository().has_owner(item_id=item["id"], user_id=user_id):
        return True
    perm = ItemPermissionRepository().get_for_user(item_id=item["id"], user_id=user_id)
    return bool(perm and perm["can_view"])


def can_edit_item(*, item: dict, campaign: dict, user_id: str) -> bool:
    if _is_gm(campaign):
        return True
    if ItemRepository().has_owner(item_id=item["id"], user_id=user_id):
        return True
    perm = ItemPermissionRepository().get_for_user(item_id=item["id"], user_id=user_id)
    return bool(perm and perm["can_edit"])
