from __future__ import annotations

from app.business.admin.admin_service import AdminService
from app.helpers.password import verify_password
from app.persistence.database import engine_connect
from app.persistence.repositories.user_repository import UserRepository
from tests.conftest import seed_campaign, seed_user


                                                                 
                                                            


def _campaign_exists(campaign_id: str) -> bool:
    with engine_connect() as conn:
        return (
            conn.exec_driver_sql("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
            is not None
        )


def test_owner_lists_users(db):
    seed_user(name="Owner", email="owner@test.com")                                
    seed_user(name="Bob", email="bob@test.com")
    emails = {u["email"] for u in AdminService().list_users()}
    assert {"owner@test.com", "bob@test.com"} <= emails


def test_delete_user_cascades_their_campaigns(db):
    owner = seed_user(email="o@test.com")
    player = seed_user(email="p@test.com")
    cid = seed_campaign(player, title="PlayerCamp")

    result = AdminService().delete_user(requester_user_id=owner, target_user_id=player)

    assert result.success
    assert UserRepository().get_by_id(player) is None
    assert not _campaign_exists(cid)                        


def test_cannot_delete_self(db):
    owner = seed_user(email="o@test.com")
    result = AdminService().delete_user(requester_user_id=owner, target_user_id=owner)
    assert not result.success
    assert result.error_key == "inside.admin.errors.cannot_delete_self"
    assert UserRepository().get_by_id(owner) is not None


def test_non_owner_blocked_on_user_delete(db):
    owner = seed_user(email="o@test.com")
    player = seed_user(email="p@test.com")
    result = AdminService().delete_user(requester_user_id=player, target_user_id=owner)
    assert not result.success
    assert result.error_key == "inside.admin.errors.not_owner"
    assert UserRepository().get_by_id(owner) is not None


def test_reset_password(db):
    owner = seed_user(email="o@test.com")
    player = seed_user(email="p@test.com")

    result = AdminService().reset_password(
        requester_user_id=owner, target_user_id=player, new_password="NewPass123!"
    )

    assert result.success
    user = UserRepository().get_by_id(player)
    assert verify_password("NewPass123!", user["password_hash"])


def test_reset_password_rejects_short(db):
    owner = seed_user(email="o@test.com")
    player = seed_user(email="p@test.com")
    result = AdminService().reset_password(
        requester_user_id=owner, target_user_id=player, new_password="short"
    )
    assert not result.success
    assert result.error_key == "inside.admin.errors.password_invalid"
