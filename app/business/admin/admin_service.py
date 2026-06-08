"""Instance-owner administration (the user whose ``system_role`` is OWNER).

The instance owner manages the registered users (list / delete / reset password).
Every method re-verifies the requester is the instance owner — the HTTP layer
gates too, but destructive ops defend in depth.
"""

from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row

from app.domain.roles import SystemRole
from app.helpers.password import hash_password
from app.helpers.validators import validate_password
from app.persistence.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class AdminResult:
    success: bool
    error_key: str | None = None


class AdminService:
    def __init__(self, *, users: UserRepository | None = None) -> None:
        self.users = users or UserRepository()

    def _is_owner(self, user_id: str) -> bool:
        user = self.users.get_by_id(user_id)
        return user is not None and str(user["system_role"]) == SystemRole.OWNER.value

                                                                             

    def list_users(self) -> list[Row]:
        return self.users.list_all()

    def delete_user(self, *, requester_user_id: str, target_user_id: str) -> AdminResult:
        if not self._is_owner(requester_user_id):
            return AdminResult(success=False, error_key="inside.admin.errors.not_owner")
        if requester_user_id == target_user_id:
            return AdminResult(success=False, error_key="inside.admin.errors.cannot_delete_self")
        target = self.users.get_by_id(target_user_id)
        if target is None:
            return AdminResult(success=False, error_key="inside.admin.errors.user_not_found")
        if str(target["system_role"]) == SystemRole.OWNER.value and self.users.count_owners() <= 1:
            return AdminResult(
                success=False, error_key="inside.admin.errors.cannot_delete_last_owner"
            )
                                                                                   
        self.users.delete(user_id=target_user_id)
        return AdminResult(success=True)

    def reset_password(
        self, *, requester_user_id: str, target_user_id: str, new_password: str
    ) -> AdminResult:
        if not self._is_owner(requester_user_id):
            return AdminResult(success=False, error_key="inside.admin.errors.not_owner")
        if self.users.get_by_id(target_user_id) is None:
            return AdminResult(success=False, error_key="inside.admin.errors.user_not_found")
        if not validate_password(new_password):
            return AdminResult(success=False, error_key="inside.admin.errors.password_invalid")
        self.users.update_password(
            user_id=target_user_id, password_hash=hash_password(new_password)
        )
        return AdminResult(success=True)
