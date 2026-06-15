from __future__ import annotations

import os

                                                                                
                                                                                 
                                                                                
                                                                                 
os.environ.setdefault("APP_ENV", "test")


os.environ.setdefault("ALLOWED_HOSTS", "testserver.local,localhost,127.0.0.1")

import time              
import uuid              

import pytest              
from litestar.middleware.csrf import generate_csrf_token              
from litestar.middleware.session.server_side import ServerSideSessionConfig              

import app.persistence.database as db_module              
from app.config import config              
from app.helpers.password import hash_password              
from app.persistence.database import engine_begin              

                                                                                  
                                                          
TEST_SESSION_CONFIG = ServerSideSessionConfig(key=config.session_cookie_name)


def login(client, user_id: str) -> str:
    """Authenticate a TestClient via a server-side session and arm CSRF.

    Sets the session cookie (user_id) + the csrftoken cookie/header so unsafe
    requests pass Litestar's CSRF middleware. Returns the CSRF token. The client
    must be created with ``session_config=TEST_SESSION_CONFIG``.
    """
    client.set_session_data({"user_id": user_id})
    token = generate_csrf_token(config.session_secret)
    client.cookies.set("csrftoken", token)
    client.headers["x-csrftoken"] = token
    return token


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Isolated SQLite database for each test via a temp file."""
    test_db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", test_db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
                                                                              
                                                                              
                                                         
    from app.persistence import engine as engine_module

    engine_module.reset_engine()
    # SDK packages are discovered from the real ``data/packages`` directory via
    # the configured data dir, so no path monkeypatching is required here.
    yield
    engine_module.reset_engine()


                                                                             
                                                                          
                          
                                                                             

def seed_user(*, name: str = "Alice", email: str | None = None) -> str:
    """Insert a user directly and return user_id."""
    from app.persistence.repositories.user_repository import UserRepository
    email = email or f"user_{uuid.uuid4().hex[:8]}@test.com"
    row = UserRepository().create_with_auto_role(
        name=name,
        email=email,
        password_hash=hash_password("Password1!"),
    )
    return row["id"]


def seed_campaign(gm_id: str, *, title: str = "Test Campaign") -> str:
    """Create a campaign owned by gm_id and return campaign_id."""
    from app.persistence.repositories.campaign_repository import CampaignRepository
    row = CampaignRepository().create(
        owner_user_id=gm_id,
        title=title,
        description="",
    )
    return row["id"]


def seed_member(campaign_id: str, user_id: str, role: str) -> None:
    """Add a user as a member of a campaign (bypasses invitation flow)."""
    now = int(time.time())
    member_id = uuid.uuid4().hex
    with engine_begin() as conn:
        conn.exec_driver_sql(
            """
            INSERT INTO campaign_members (id, campaign_id, user_id, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (member_id, campaign_id, user_id, role, now, now),
        )


def install_system(gm_id: str, *, package_id: str = "dnd5e") -> str:
    """Install + enable a bundled SDK package. Returns its package id."""
    from app.engine.sdk.package_install_service import PackageInstallService
    svc = PackageInstallService()
    installed = svc.install(package_id=package_id, user_id=gm_id)
    assert installed.success, f"install failed: {installed.error_key}"
    enabled = svc.enable(package_id=package_id)
    assert enabled.success, f"enable failed: {enabled.error_key}"
    return installed.package_id or package_id


def seed_system(campaign_id: str, gm_id: str, package_id: str = "dnd5e") -> str:
    """Install + enable a manifest system and assign it to a campaign. Returns system_id."""
    from app.business.campaigns.campaign_system_service import CampaignSystemService
    system_id = install_system(gm_id, package_id=package_id)
    result = CampaignSystemService().assign_to_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id=system_id,
    )
    assert result.success, f"seed_system failed: {result.error_key}"
    return system_id


def seed_actor(
    campaign_id: str,
    gm_id: str,
    *,
    name: str = "Test Actor",
    actor_type: str = "character",
    system_id: str = "dnd5e",
    data: dict | None = None,
    owner_user_ids: list[str] | None = None,
) -> str:
    """Create an Actor Core row (+ optional sheet data) and return actor_id.

    The system must already be installed (use seed_system / install_system first).
    """
    from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
    from app.persistence.repositories.actor_repository import ActorRepository
    actor_id = ActorRepository().create(
        campaign_id=campaign_id,
        system_id=system_id,
        actor_type=actor_type,
        name=name,
        created_by_user_id=gm_id,
        owner_user_ids=owner_user_ids or [],
    )
    ScopedJsonStorage().write_actor(
        system_id=system_id,
        campaign_id=campaign_id,
        actor_id=actor_id,
        version=1,
        data=data or {},
    )
    return actor_id


def grant_actor_access(actor_id: str, user_id: str, *, view: bool = False, edit: bool = False) -> None:
    """Grant a player view/edit access to an actor (mirrors set_member_access)."""
    from app.persistence.repositories.actor_permission_repository import ActorPermissionRepository
    ActorPermissionRepository().upsert_for_user(
        actor_id=actor_id, user_id=user_id, can_view=view or edit, can_edit=edit
    )


def seed_scene(campaign_id: str, *, name: str = "Test Scene") -> dict:
    """Create a scene and return the scene row."""
    from app.persistence.repositories.scene_repository import SceneRepository
    return SceneRepository().create(
        campaign_id=campaign_id,
        name=name,
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
