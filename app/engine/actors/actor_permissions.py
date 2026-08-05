"""Server-authoritative permission checks for actors (§17).

Mirrors the journals model: the GM always passes; other users are granted
view/edit only via explicit ownership (``actor_owners``) or a per-user
``actor_permissions`` row — never by the client.
"""

from __future__ import annotations

from app.domain.roles import has_full_view
from app.persistence.repositories.actor_permission_repository import ActorPermissionRepository
from app.persistence.repositories.actor_repository import ActorRepository

_actors = ActorRepository()
_permissions = ActorPermissionRepository()


def _is_gm(campaign: dict) -> bool:
    return campaign.get("member_role") == "gm"


def can_view_actor(*, actor: dict, campaign: dict, user_id: str) -> bool:
                                                                
    if has_full_view(campaign.get("member_role")):
        return True
    if _actors.has_owner(actor_id=actor["id"], user_id=user_id):
        return True
    permission = _permissions.get_for_user(actor_id=actor["id"], user_id=user_id)
    return bool(permission and permission["can_view"])


def can_edit_actor(*, actor: dict, campaign: dict, user_id: str) -> bool:
    if _is_gm(campaign):
        return True
    if _actors.has_owner(actor_id=actor["id"], user_id=user_id):
        return True
    permission = _permissions.get_for_user(actor_id=actor["id"], user_id=user_id)
    return bool(permission and permission["can_edit"])
