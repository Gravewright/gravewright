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
    GM_EMAIL, GM_PASSWORD, PLAYER_EMAIL, PLAYER_PASSWORD, REPO_ROOT,
    _free_port, _seed_database, _wait_http_ready,
)
from tests.e2e.test_multiplayer_playwright import _close, _login


PACKAGE_ID = "gravewright-3d-dice"


@pytest.fixture(scope="module")
def dice_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gravewright-3d-dice")
    db_path = tmp / "e2e.sqlite3"
    seeded = _seed_database(db_path)
    data = tmp / "data"
    target = data / "packages/addons" / PACKAGE_ID
    target.parent.mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "data/packages/addons" / PACKAGE_ID, target)
    text = (target / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(text)

    import app.persistence.database as db_module
    from app.business.users import UserPreferenceService
    from app.persistence import engine as engine_module
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
    from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
    from app.persistence.repositories.scene_repository import SceneRepository
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.campaign_repository import CampaignRepository
    from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
    from tests.conftest import seed_scene

    db_module.DATABASE_PATH = db_path.resolve()
    db_module._initialized = False
    engine_module.reset_engine()
    scene = seed_scene(seeded["campaign_id"])
    SceneRepository().set_active_scene(campaign_id=seeded["campaign_id"], scene_id=scene["id"])
    UserPreferenceService().set_ping_color(user_id=seeded["gm_id"], ping_color="#8b5cf6")
    UserPreferenceService().set_ping_color(user_id=seeded["player_id"], ping_color="#2563eb")
    InstalledPackageRepository().upsert(
        package_id=PACKAGE_ID, kind="addon", name=manifest["name"], version=manifest["version"],
        status="enabled", package_dir=f"addons/{PACKAGE_ID}", manifest_json=text,
        compatibility_status="compatible", validation_errors_json="[]",
        installed_by_user_id=seeded["gm_id"], last_validation_status="valid",
    )
    CampaignPackageRepository().activate(
        campaign_id=seeded["campaign_id"], package_id=PACKAGE_ID,
        activation_role="addon", enabled_by_user_id=seeded["gm_id"],
    )
    ruleset_id = "savage-worlds"
    ruleset_target = data / "packages/rulesets" / ruleset_id
    ruleset_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "data/packages/rulesets" / ruleset_id, ruleset_target)
    ruleset_text = (ruleset_target / "manifest.json").read_text(encoding="utf-8")
    ruleset_manifest = json.loads(ruleset_text)
    InstalledPackageRepository().upsert(
        package_id=ruleset_id, kind="ruleset", name=ruleset_manifest["name"], version=ruleset_manifest["version"],
        status="enabled", package_dir=f"rulesets/{ruleset_id}", manifest_json=ruleset_text,
        compatibility_status="compatible", validation_errors_json="[]",
        installed_by_user_id=seeded["gm_id"], last_validation_status="valid",
    )
    CampaignRepository().update_system(
        campaign_id=seeded["campaign_id"], changed_by_user_id=seeded["gm_id"], next_system_id=ruleset_id,
    )
    seeded["savage_actor_id"] = ActorRepository().create(
        campaign_id=seeded["campaign_id"], system_id=ruleset_id, actor_type="character",
        name="Dice Sheet Hero", created_by_user_id=seeded["gm_id"],
    )
    ScopedJsonStorage().write_actor(
        system_id=ruleset_id, campaign_id=seeded["campaign_id"], actor_id=seeded["savage_actor_id"],
        version=1,
        data={
            "attributes": {"agility": {"sides": 4, "modifier": 0}},
            "wildDie": {"sides": 6},
            "penalty": {"physical": 0},
        },
    )
    engine_module.reset_engine()

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update({
        "APP_ENV": "test", "DATABASE_URL": f"sqlite:///{db_path.resolve().as_posix()}",
        "ALLOWED_HOSTS": "*", "WS_ALLOWED_ORIGINS": base, "SESSION_COOKIE_SECURE": "false",
        "ALLOW_METADATA_BOOTSTRAP": "true", "GRAVEWRIGHT_TEST_TEMP_ROOT": str(tmp.resolve()),
        "GRAVEWRIGHT_DATA_DIR": str(data.resolve()),
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO_ROOT), env=env,
    )
    try:
        _wait_http_ready(f"{base}/login", proc=proc)
        yield {"base_url": base, "scene_id": scene["id"], **seeded}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()


def _open_dice(page, campaign_id):
    opener = page.locator(f'[data-modal-open="dice-tray-{campaign_id}"]')
    if not opener.is_visible():
        page.locator(f'[data-panel-toggle="panel-chat-{campaign_id}"]').click()
    opener.click()
    tray = page.locator(f'[data-dice-tray][data-room-id="{campaign_id}"]')
    expect(tray).to_be_visible()
    return tray


def _start_roll(page, tray, expression, visibility="public"):
    page.locator(".gravewright-3d-dice").wait_for(state="attached")
    page.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
    if not tray.is_visible():
        _open_dice(page, tray.get_attribute("data-room-id"))
    tray.locator("[data-dice-formula]").fill(expression)
    tray.locator(f'[data-dice-roll="{visibility}"]').click()
    page.wait_for_function("Number(document.querySelector('.gravewright-3d-dice')?.dataset.activeDice || 0) > 0")
    expect(page.locator(".gravewright-3d-dice-tray")).to_have_css("opacity", "0.94")
    assert "dice-tray-top-down.png" in page.locator(".gravewright-3d-dice-tray").evaluate("node => getComputedStyle(node).backgroundImage")
    page.wait_for_function("Number(document.querySelector('.gravewright-3d-dice')?.dataset.wallImpacts || 0) > 0")
    return page.locator(".gravewright-3d-dice").get_attribute("data-results")


def _roll(page, tray, expression, visibility="public"):
    authoritative = _start_roll(page, tray, expression, visibility)
    expected_count = len(authoritative.split(","))
    page.wait_for_function("expected => (document.querySelector('.gravewright-3d-dice')?.dataset.finalResults?.split(',').filter(Boolean).length || 0) === expected", arg=expected_count)
    final_visible = page.locator(".gravewright-3d-dice").get_attribute("data-final-results")
    assert final_visible == authoritative
    return authoritative


def test_real_roll_matrix_author_color_privacy_and_cleanup(dice_server):
    server = dice_server
    base = server["base_url"]
    url = f"{base}/game?room={server['campaign_id']}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        gm_context = browser.new_context(reduced_motion="reduce")
        player_context = browser.new_context(reduced_motion="reduce")
        try:
            gm = gm_context.new_page()
            player = player_context.new_page()
            _login(gm, base, GM_EMAIL, GM_PASSWORD)
            _login(player, base, PLAYER_EMAIL, PLAYER_PASSWORD)
            gm.goto(url)
            player.goto(url)
            tray_asset = gm.request.get(f"{base}/sdk/packages/{PACKAGE_ID}/asset/assets/dice-tray-top-down.png")
            assert tray_asset.status == 200
            assert tray_asset.headers["content-type"].startswith("image/png")
            gm.locator("[data-onboarding-close]").first.click()
            player.reload()
            gm.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")
            player.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")
            gm_tray = _open_dice(gm, server["campaign_id"])
            player_tray = _open_dice(player, server["campaign_id"])

            for expression, expected_faces in [
                ("1d4", "4:"), ("1d6", "6:"), ("1d8", "8:"), ("1d10", "10:"),
                ("1d12", "12:"), ("1d20", "20:"), ("1d%", "10:"),
                ("2d6", "6:"), ("4d6", "6:"), ("2d8+1d6+3", "8:"),
            ]:
                results = _roll(gm, gm_tray, expression)
                assert expected_faces in results
                assert gm.locator(".gravewright-3d-dice").get_attribute("data-colors") == "#8b5cf6"
                player.wait_for_function("Number(document.querySelector('.gravewright-3d-dice')?.dataset.activeDice || 0) > 0")
                assert player.locator(".gravewright-3d-dice").get_attribute("data-colors") == "#8b5cf6"

            expect(gm_tray).to_be_hidden()
            gm.locator(f'[data-panel-toggle="panel-settings-{server["campaign_id"]}"]').click()
            color_input = gm.locator("[data-ping-color-input]").first
            color_input.evaluate("input => { input.value = '#ef4444'; input.dispatchEvent(new Event('change', {bubbles: true})); }")
            gm.wait_for_function("document.body.dataset.pingColor === '#ef4444'")
            gm.locator(f'[data-modal-id="panel-settings-{server["campaign_id"]}"] [data-modal-close]').click()
            gm_tray = _open_dice(gm, server["campaign_id"])
            _roll(gm, gm_tray, "1d20")
            assert gm.locator(".gravewright-3d-dice").get_attribute("data-colors") == "#ef4444"

            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            expect(gm_tray).to_be_hidden()
            gm.locator(f'[data-panel-toggle="panel-actors-{server["campaign_id"]}"]').click()
            gm.locator(f'[data-actor-open="{server["savage_actor_id"]}"]').click()
            sheet = gm.locator(f'[data-actor-sheet-root][data-actor-id="{server["savage_actor_id"]}"]')
            expect(sheet).to_be_visible()
            sheet.locator('[data-action="roll.trait.agility"]').click()
            roll_dialog = gm.locator(".gw-roll-dialog")
            expect(roll_dialog).to_be_visible()
            with gm.expect_response(lambda response: response.url.endswith("/game/actor/action")) as action_response:
                roll_dialog.locator(".gw-roll-dialog__btn--primary").click()
            response = action_response.value
            assert response.status == 200, response.text()
            assert response.json().get("groups"), response.json()
            gm.wait_for_function("Number(document.querySelector('.gravewright-3d-dice')?.dataset.activeDice || 0) > 0")
            gm.wait_for_function("Number(document.querySelector('.gravewright-3d-dice')?.dataset.wallImpacts || 0) > 0")
            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            gm.locator(f'[data-modal-id="actor-{server["savage_actor_id"]}"] [data-modal-close]').click()
            gm.locator(f'[data-panel-toggle="panel-actors-{server["campaign_id"]}"]').click()
            gm_tray = _open_dice(gm, server["campaign_id"])

            _roll(player, player_tray, "1d6")
            assert player.locator(".gravewright-3d-dice").get_attribute("data-colors") == "#2563eb"
            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.colors === '#2563eb'")

            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            player.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            player_tray = _open_dice(player, server["campaign_id"])
            gm_tray.locator("[data-dice-formula]").fill("1d20")
            player_tray.locator("[data-dice-formula]").fill("1d6")
            gm_tray.locator('[data-dice-roll="public"]').click()
            player_tray.locator('[data-dice-roll="public"]').click()
            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.colors?.includes('#ef4444') && document.querySelector('.gravewright-3d-dice')?.dataset.colors?.includes('#2563eb')")
            player.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.colors?.includes('#ef4444') && document.querySelector('.gravewright-3d-dice')?.dataset.colors?.includes('#2563eb')")
            assert set(gm.locator(".gravewright-3d-dice").get_attribute("data-colors").split(",")) == {"#ef4444", "#2563eb"}

            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            player.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            _roll(gm, gm_tray, "1d20", visibility="gm")
            player.wait_for_timeout(300)
            assert player.locator(".gravewright-3d-dice").get_attribute("data-active-dice") == "0"

            gm.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'")
            assert gm.locator(".gravewright-3d-dice").get_attribute("data-physics-bodies") == "0"
            gm.reload()
            expect(gm.locator(".gravewright-3d-dice")).to_have_count(1)
            assert gm.locator(".gravewright-3d-dice").get_attribute("data-active-dice") == "0"
        finally:
            _close(player_context)
            _close(gm_context)
            browser.close()


def test_bounded_performance_for_one_to_fifty_real_dice(dice_server):
    server = dice_server
    base = server["base_url"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        try:
            page = context.new_page()
            addon_http_errors = []
            page.on("response", lambda response: addon_http_errors.append((response.status, response.url)) if response.status >= 400 and PACKAGE_ID in response.url else None)
            _login(page, base, GM_EMAIL, GM_PASSWORD)
            page.goto(f"{base}/game?room={server['campaign_id']}")
            page.locator("[data-onboarding-close]").first.click()
            page.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")
            tray = _open_dice(page, server["campaign_id"])
            measurements = []
            for count in (1, 5, 10, 20, 50):
                started = page.evaluate("performance.now()")
                results = _start_roll(page, tray, f"{count}d6")
                assert len(results.split(",")) == count
                assert page.locator(".gravewright-3d-dice").get_attribute("data-final-results") == ""
                spawn_ms = page.evaluate("started => performance.now() - started", started)
                page.wait_for_function("expected => (document.querySelector('.gravewright-3d-dice')?.dataset.finalResults?.split(',').filter(Boolean).length || 0) === expected", arg=count)
                assert page.locator(".gravewright-3d-dice").get_attribute("data-final-results") == results
                page.wait_for_function("document.querySelector('.gravewright-3d-dice')?.dataset.activeDice === '0'", timeout=6000)
                measurements.append({
                    "count": count,
                    "spawn_ms": spawn_ms,
                    "average_frame_ms": float(page.locator(".gravewright-3d-dice").get_attribute("data-average-frame-ms")),
                    "max_frame_ms": float(page.locator(".gravewright-3d-dice").get_attribute("data-max-frame-ms")),
                })
            print("3D DICE PERFORMANCE", measurements)
            assert all(item["spawn_ms"] < 1500 for item in measurements)
            assert measurements[-1]["average_frame_ms"] < 16
            assert page.locator(".gravewright-3d-dice").get_attribute("data-physics-bodies") == "0"
            assert page.locator(".gravewright-3d-dice").get_attribute("data-queued-rolls") == "0"
            expect(page.locator(".gravewright-3d-dice-tray")).to_be_hidden()
            assert addon_http_errors == []
        finally:
            _close(context)
            browser.close()
