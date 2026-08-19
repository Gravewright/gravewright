from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import pytest
from playwright.sync_api import expect, sync_playwright

from tests.e2e.test_app_server_e2e import (
    GM_EMAIL,
    GM_PASSWORD,
    PLAYER_EMAIL,
    PLAYER_PASSWORD,
    REPO_ROOT,
    _free_port,
    _seed_database,
    _wait_http_ready,
)
from tests.e2e.test_multiplayer_playwright import _close, _login


PACKAGE_ID = "directed-interactions-e2e"


@pytest.fixture(scope="module")
def directed_interactions_server(tmp_path_factory):
    """Real server with only the disposable public-SDK test addon activated."""
    tmp_dir = tmp_path_factory.mktemp("directed-interactions-e2e")
    db_path = tmp_dir / "e2e.sqlite3"
    seeded = _seed_database(db_path)

    package_source = (
        REPO_ROOT
        / "tests/fixtures/sdk_packages/valid/addons/directed-interactions-e2e"
    )
    data_dir = tmp_dir / "data"
    package_dir = data_dir / "packages/addons" / PACKAGE_ID
    package_dir.parent.mkdir(parents=True)
    shutil.copytree(package_source, package_dir)
    manifest_text = (package_dir / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    import app.persistence.database as db_module
    from app.persistence import engine as engine_module
    from app.persistence.repositories.campaign_package_repository import (
        CampaignPackageRepository,
    )
    from app.persistence.repositories.installed_package_repository import (
        InstalledPackageRepository,
    )

    db_module.DATABASE_PATH = db_path.resolve()
    db_module._initialized = False
    engine_module.reset_engine()
    InstalledPackageRepository().upsert(
        package_id=PACKAGE_ID,
        kind="addon",
        name=manifest["name"],
        version=manifest["version"],
        status="enabled",
        package_dir=f"addons/{PACKAGE_ID}",
        manifest_json=manifest_text,
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=seeded["gm_id"],
        last_validation_status="valid",
    )
    CampaignPackageRepository().activate(
        campaign_id=seeded["campaign_id"],
        package_id=PACKAGE_ID,
        activation_role="addon",
        enabled_by_user_id=seeded["gm_id"],
    )
    engine_module.reset_engine()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": f"sqlite:///{db_path.resolve().as_posix()}",
            "ALLOWED_HOSTS": "*",
            "WS_ALLOWED_ORIGINS": base_url,
            "SESSION_COOKIE_SECURE": "false",
            "ALLOW_METADATA_BOOTSTRAP": "true",
            "GRAVEWRIGHT_TEST_TEMP_ROOT": str(tmp_dir.resolve()),
            "GRAVEWRIGHT_DATA_DIR": str(data_dir.resolve()),
        }
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO_ROOT),
        env=env,
    )
    try:
        _wait_http_ready(f"{base_url}/login", proc=proc)
        yield {"base_url": base_url, **seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()


def test_directed_interaction_survives_player_reload(directed_interactions_server) -> None:
    """Cover request, delivery, authenticated response, and reload recovery."""
    server = directed_interactions_server
    base_url = server["base_url"]
    game_url = f"{base_url}/game?room={server['campaign_id']}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        gm_context = browser.new_context()
        player_context = browser.new_context()
        try:
            gm = gm_context.new_page()
            player = player_context.new_page()
            _login(gm, base_url, GM_EMAIL, GM_PASSWORD)
            _login(player, base_url, PLAYER_EMAIL, PLAYER_PASSWORD)
            gm.goto(game_url)
            player.goto(game_url)
            # Complete the persisted first-visit transition before exercising reload.
            gm.locator("[data-onboarding-close]").first.click()
            player.reload()

            controls = gm.get_by_test_id("directed-interactions-e2e-controls")
            expect(controls).to_be_attached()
            recipient = gm.get_by_test_id("directed-interactions-recipient")
            title = gm.get_by_test_id("directed-interactions-title")
            prompt = gm.get_by_test_id("directed-interactions-prompt")
            create = gm.get_by_test_id("directed-interactions-create")
            state = gm.get_by_test_id("directed-interactions-state")

            recipient.fill(server["player_id"])
            title.fill("Reaction Test")
            prompt.fill("Use your reaction?")
            create.click()

            dialog = player.get_by_test_id("directed-interaction")
            expect(dialog).to_be_visible()
            expect(player.get_by_test_id("directed-interaction-title")).to_have_text(
                "Reaction Test"
            )
            # The GM is not a recipient, so no core response UI is presented there.
            expect(gm.get_by_test_id("directed-interaction")).to_have_count(0)
            player.get_by_test_id("directed-interaction-response").check()
            player.get_by_test_id("directed-interaction-submit").click()
            expect(dialog).to_have_count(0)
            expect(state).to_contain_text('"status":"completed"')
            expect(state).to_contain_text(server["player_id"])
            expect(state).to_contain_text("true")

            title.fill("Reload Test")
            prompt.fill("Still ready?")
            create.click()
            expect(player.get_by_test_id("directed-interaction-title")).to_have_text(
                "Reload Test"
            )

            # A genuine document navigation destroys the old modal and runtime.
            response = player.reload()
            assert response is not None and response.ok
            reconstructed = player.get_by_test_id("directed-interaction")
            expect(reconstructed).to_be_visible()
            expect(player.get_by_test_id("directed-interaction-title")).to_have_text(
                "Reload Test"
            )
            expect(player.get_by_test_id("directed-interaction-prompt")).to_have_text(
                "Still ready?"
            )
            player.get_by_test_id("directed-interaction-response").check()
            player.get_by_test_id("directed-interaction-submit").click()
            expect(reconstructed).to_have_count(0)
            expect(state).to_contain_text('"title":"Reload Test"')
            expect(state).to_contain_text('"status":"completed"')
            expect(state).to_contain_text(server["player_id"])
            expect(state).to_contain_text("true")
        finally:
            _close(player_context)
            _close(gm_context)
            browser.close()
