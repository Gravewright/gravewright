from __future__ import annotations

import os

                                                                                
                                                                                 
                                                                                
                                                                                 
os.environ.setdefault("APP_ENV", "test")


os.environ.setdefault("ALLOWED_HOSTS", "testserver.local,localhost,127.0.0.1")

import time              
import uuid              
from pathlib import Path

import pytest              
from litestar.middleware.csrf import generate_csrf_token              
from litestar.middleware.session.server_side import ServerSideSessionConfig              

import app.persistence.database as db_module              
from app.config import config              
from app.helpers.password import hash_password              
from app.persistence.database import engine_begin              

SDK_FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "sdk_packages" / "valid"

                                                                                  
                                                          
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
    from app.engine.sdk import package_registry

    monkeypatch.setattr(package_registry, "PACKAGES_DIR", SDK_FIXTURES_ROOT)
    monkeypatch.setattr(
        package_registry,
        "STORAGE_PACKAGES_DIR",
        tmp_path / "storage" / "packages",
    )
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


def install_system(user_id: str, *, package_id: str = "valid-ruleset") -> str:
    """Install and enable a package globally, returning its package id."""
    from app.engine.sdk.package_install_service import PackageInstallService

    service = PackageInstallService()
    installed = service.install(package_id=package_id, user_id=user_id)
    assert installed.success, installed.error_key
    enabled = service.enable(package_id=package_id)
    assert enabled.success, enabled.error_key
    return package_id


def seed_system(campaign_id: str, user_id: str, package_id: str = "valid-ruleset") -> str:
    """Install, enable, and activate a ruleset package for a campaign."""
    from app.engine.sdk.package_activation_service import PackageActivationService

    install_system(user_id, package_id=package_id)
    activated = PackageActivationService().set_campaign_ruleset(
        campaign_id, package_id, user_id
    )
    assert activated.success, activated.error_key
    return package_id


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
