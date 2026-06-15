from __future__ import annotations

from litestar.testing import TestClient

from app.engine.sdk.package_dependency_service import (
    DependencyReport,
    PackageDependencyService,
)
from tests.conftest import (
    TEST_SESSION_CONFIG,
    install_system,
    login,
    seed_campaign,
    seed_system,
    seed_user,
)


def test_blocking_error_keys_lists_every_reason():
    report = DependencyReport(
        ok=False,
        missing=[{"id": "a"}],
        disabled=[{"id": "b"}],
        conflicts=[{"id": "c"}],
    )

    keys = PackageDependencyService.blocking_error_keys(report)

    assert keys == [
        "sdk.errors.dependency_missing",
        "sdk.errors.dependency_disabled",
        "sdk.errors.package_conflict_active",
    ]
    # first_error_key stays consistent with the full list.
    assert PackageDependencyService.first_error_key(report) == keys[0]


def test_blocking_error_keys_empty_when_ok():
    assert PackageDependencyService.blocking_error_keys(DependencyReport()) == []


def test_inside_reinforces_trusted_code_confirm_on_scripted_install(db):
    """A scripted package (declares assets.scripts) must carry the trusted-code
    confirm on its install/enable flow, not only in the detail modal."""
    from main import app

    owner = seed_user(name="Owner", email="owner-trusted-confirm@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner)
        resp = client.get("/inside", follow_redirects=False)

    assert resp.status_code == 200
    # dice-so-nice-lite is a scripted, installable addon → confirm on its form.
    assert "data-confirm=" in resp.text
    assert ("trust the author" in resp.text) or ("confiar no autor" in resp.text)


def test_inside_renders_campaign_package_modal_with_active_addon(db):
    """The per-campaign modal lists activatable addons; a clean addon has no
    blockers and an enabled activate button."""
    from main import app

    owner = seed_user(name="Owner", email="owner-pkg-modal@test.com")
    campaign = seed_campaign(owner)
    seed_system(campaign, owner, "dnd5e")
    install_system(owner, package_id="dice-so-nice-lite")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner)
        resp = client.get("/inside", follow_redirects=False)

    assert resp.status_code == 200
    assert "campaign-package-list" in resp.text
    assert "/sdk/campaigns/packages/activate" in resp.text
