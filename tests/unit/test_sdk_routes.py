from __future__ import annotations

from litestar.testing import TestClient

from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import (
    TEST_SESSION_CONFIG,
    login,
    seed_campaign,
    seed_system,
    seed_user,
)


def test_sdk_packages_listing(db):
    from main import app

    user_id = seed_user(name="Owner", email="sdk-list@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        resp = client.get("/sdk/packages")

    assert resp.status_code == 200
    packages = resp.json()["packages"]
    ids = {p["id"] for p in packages}
    assert {"dnd5e", "dice-so-nice-lite"} <= ids
    by_id = {p["id"]: p for p in packages}
    assert by_id["dnd5e"]["trusted_code_required"] is True
    assert by_id["dice-so-nice-lite"]["scripted"] is True


def test_sdk_package_detail_and_404(db):
    from main import app

    user_id = seed_user(name="Owner", email="sdk-detail@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        ok = client.get("/sdk/packages/dnd5e")
        missing = client.get("/sdk/packages/nope")

    assert ok.status_code == 200
    assert ok.json()["kind"] == "ruleset"
    assert missing.status_code == 404


def test_sdk_asset_serving_only_declared_files(db):
    from main import app

    gm_id = seed_user(name="GM", email="sdk-asset@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)  # installs + enables + assigns dnd5e

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        declared = client.get("/sdk/packages/dnd5e/asset/assets/dnd5e.css")
        undeclared = client.get("/sdk/packages/dnd5e/asset/manifest.json")
        traversal = client.get("/sdk/packages/dnd5e/asset/../../../etc/passwd")

    assert declared.status_code == 200
    assert "text/css" in declared.headers["content-type"]
    assert undeclared.status_code == 404
    assert traversal.status_code in {404, 400}


def test_sdk_install_is_owner_gated(db):
    from main import app

    # A fresh non-owner user must not be able to install globally.
    owner = seed_user(name="Owner", email="sdk-owner@test.com")
    player = seed_user(name="Player", email="sdk-player@test.com")
    assert PackageInstallService().get("dice-so-nice-lite") is None

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        resp = client.post(
            "/sdk/packages/install",
            data={"package_id": "dice-so-nice-lite"},
            follow_redirects=False,
        )

    assert resp.status_code in {302, 303}
    # Non-owner install must be a no-op.
    assert PackageInstallService().get("dice-so-nice-lite") is None
    _ = owner


def test_sdk_campaign_package_activation_form_redirects(db):
    from main import app

    gm_id = seed_user(name="GM", email="sdk-campaign-package@test.com")
    campaign_id = seed_campaign(gm_id)
    packages = PackageInstallService()
    assert packages.install(package_id="dice-so-nice-lite", user_id=gm_id).success
    assert packages.enable(package_id="dice-so-nice-lite").success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/sdk/campaigns/packages/activate",
            data={"campaign_id": campaign_id, "package_id": "dice-so-nice-lite"},
            follow_redirects=False,
        )

    assert resp.status_code in {302, 303}
    active_ids = {
        package["package_id"]
        for package in PackageActivationService().list_campaign_packages(campaign_id)
    }
    assert "dice-so-nice-lite" in active_ids
