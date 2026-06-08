from __future__ import annotations

from dataclasses import dataclass

from app.domain.permissions.defaults import DEFAULT_ROLE_PERMISSIONS
from app.domain.permissions.groups import ALL_CORE_PERMISSION_KEYS
from app.domain.permissions.groups import CONFIGURABLE_ROLES
from app.domain.permissions.groups import CORE_PERMISSION_GROUPS
from app.domain.permissions.groups import DISPLAY_ROLES
from app.domain.permissions.permissions import PermissionEffect
from app.domain.permissions.permissions import PermissionSubjectType
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_permission_repository import CampaignPermissionRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class PermissionUpdateResult:
    success: bool
    message_key: str | None = None
    error_key: str | None = None


class PermissionService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.permissions = CampaignPermissionRepository()

    def can(
        self,
        *,
        user_id: str,
        campaign_id: str,
        permission: TablePermission | str,
    ) -> bool:
        permission_key = str(permission.value if isinstance(permission, TablePermission) else permission)

        member_role = self.campaigns.get_member_role(
            campaign_id=campaign_id,
            user_id=user_id,
        )

        if member_role is None:
            return False

        if member_role == PlayerRole.GM.value and permission_key in ALL_CORE_PERMISSION_KEYS:
            return True

        user_effects = self.permissions.list_subject_effects(
            campaign_id=campaign_id,
            subject_type=PermissionSubjectType.USER,
            subject_id=user_id,
        )

        if permission_key in user_effects:
            return user_effects[permission_key] == PermissionEffect.ALLOW

        role_effects = self.permissions.list_subject_effects(
            campaign_id=campaign_id,
            subject_type=PermissionSubjectType.ROLE,
            subject_id=member_role,
        )

        if permission_key in role_effects:
            return role_effects[permission_key] == PermissionEffect.ALLOW

        return permission_key in DEFAULT_ROLE_PERMISSIONS.get(member_role, set())

    def get_default_allowed_keys_for_role(
        self,
        role: str,
    ) -> set[str]:
        if role == PlayerRole.GM.value:
            return set(ALL_CORE_PERMISSION_KEYS)

        return set(DEFAULT_ROLE_PERMISSIONS.get(role, set()))

    def _can_from_effects(
        self,
        *,
        member_role: str,
        permission_key: str,
        user_effects: dict[str, PermissionEffect],
        role_effects: dict[str, PermissionEffect],
    ) -> bool:
        if member_role == PlayerRole.GM.value and permission_key in ALL_CORE_PERMISSION_KEYS:
            return True

        if permission_key in user_effects:
            return user_effects[permission_key] == PermissionEffect.ALLOW

        if permission_key in role_effects:
            return role_effects[permission_key] == PermissionEffect.ALLOW

        return permission_key in DEFAULT_ROLE_PERMISSIONS.get(member_role, set())

    def _get_allowed_keys_for_role_from_effects(
        self,
        role: str,
        role_effects: dict[str, PermissionEffect],
    ) -> set[str]:
        allowed = self.get_default_allowed_keys_for_role(role)

        for permission_key, effect in role_effects.items():
            if permission_key not in ALL_CORE_PERMISSION_KEYS:
                continue

            if effect == PermissionEffect.ALLOW:
                allowed.add(permission_key)
            else:
                allowed.discard(permission_key)

        return allowed

    def build_settings_context(
        self,
        *,
        campaign_id: str,
        user_id: str,
        member_role: str | None = None,
    ) -> dict:
        if member_role is None:
            member_role = self.campaigns.get_member_role(
                campaign_id=campaign_id,
                user_id=user_id,
            )

        if member_role is None:
            return {
                "can_view": False,
                "can_update_permissions": False,
                "can_invite": False,
                "groups": [],
                "roles": [],
            }

                                                                           
        all_role_effects = self.permissions.list_all_role_effects_for_campaign(
            campaign_id=campaign_id,
        )

                                                              
        user_effects = self.permissions.list_subject_effects(
            campaign_id=campaign_id,
            subject_type=PermissionSubjectType.USER,
            subject_id=user_id,
        )

        role_effects = all_role_effects.get(member_role, {})

        can_view = self._can_from_effects(
            member_role=member_role,
            permission_key=TablePermission.SETTINGS_VIEW.value,
            user_effects=user_effects,
            role_effects=role_effects,
        )
        can_update_permissions = self._can_from_effects(
            member_role=member_role,
            permission_key=TablePermission.SETTINGS_UPDATE_PERMISSIONS.value,
            user_effects=user_effects,
            role_effects=role_effects,
        )
        can_invite = self._can_from_effects(
            member_role=member_role,
            permission_key=TablePermission.CAMPAIGN_INVITE_MEMBERS.value,
            user_effects=user_effects,
            role_effects=role_effects,
        )

        groups = [
            {
                "key": group["key"],
                "label_key": group["label_key"],
                "permissions": [
                    {
                        "key": permission.value,
                        "title_key": f"permissions.keys.{permission.value}.title",
                        "description_key": f"permissions.keys.{permission.value}.description",
                    }
                    for permission in group["permissions"]
                ],
            }
            for group in CORE_PERMISSION_GROUPS
        ]

        roles = [
            {
                "role": role,
                "label_key": f"roles.campaign.{role}",
                "locked": role == PlayerRole.GM.value,
                "allowed_keys": sorted(
                    self._get_allowed_keys_for_role_from_effects(
                        role, all_role_effects.get(role, {})
                    )
                ),
            }
            for role in DISPLAY_ROLES
        ]

        return {
            "can_view": can_view,
            "can_update_permissions": can_update_permissions,
            "can_invite": can_invite,
            "groups": groups,
            "roles": roles,
        }

    def _build_effects_for_role(
        self,
        *,
        role: str,
        selected_permission_keys: list[str],
    ) -> dict[str, PermissionEffect]:
        selected = {
            permission_key
            for permission_key in selected_permission_keys
            if permission_key in ALL_CORE_PERMISSION_KEYS
        }

        default_allowed = self.get_default_allowed_keys_for_role(role)
        effects: dict[str, PermissionEffect] = {}

        for permission_key in ALL_CORE_PERMISSION_KEYS:
            is_default_allowed = permission_key in default_allowed
            is_selected = permission_key in selected

            if is_selected and not is_default_allowed:
                effects[permission_key] = PermissionEffect.ALLOW

            if not is_selected and is_default_allowed:
                effects[permission_key] = PermissionEffect.DENY

        return effects

    def update_roles_permissions(
        self,
        *,
        campaign_id: str,
        user_id: str,
        role_permissions: dict[str, list[str]],
    ) -> PermissionUpdateResult:
        if not self.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SETTINGS_UPDATE_PERMISSIONS,
        ):
            return PermissionUpdateResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        for role in CONFIGURABLE_ROLES:
            effects = self._build_effects_for_role(
                role=role,
                selected_permission_keys=role_permissions.get(role, []),
            )

            self.permissions.replace_subject_effects(
                campaign_id=campaign_id,
                subject_type=PermissionSubjectType.ROLE,
                subject_id=role,
                effects=effects,
            )

        return PermissionUpdateResult(
            success=True,
            message_key="permissions.updated",
        )