"""Real-browser end-to-end test for the SDK package runtime.

Exercises the full operator + runtime path that unit/smoke tests can only
approximate:

    install -> enable -> activate (per campaign) -> open the table in a real
    browser -> the package <script> tags load -> dnd5e and dice-so-nice-lite
    register through ``window.GravewrightSDK`` -> capabilities, settings and
    locale payloads are present in the client.

How it works:

* The database is seeded **in-process** against a temporary SQLite file (the
  bundled packages are only *recorded* in the DB; their files are still served
  from ``data/packages``).
* A real ``uvicorn`` server is launched in a subprocess pointed at the same
  SQLite file via ``DATABASE_URL``.
* Selenium drives a headless Firefox: it performs a genuine form login and then
  loads ``/game``. Assertions read ``window.GravewrightSDKDebug`` (gated on
  ``APP_DEBUG``) to confirm which packages actually registered a runtime.

The whole module skips cleanly when Selenium or a Firefox/geckodriver pair is
not available, so it never breaks a browserless CI lane.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# Selenium pulls in libraries that emit DeprecationWarnings; the project turns
# warnings into errors, so scope an ignore to this browser-only module.
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

selenium = pytest.importorskip("selenium", reason="selenium not installed")

from selenium import webdriver  # noqa: E402
from selenium.common.exceptions import WebDriverException  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.firefox.options import Options as FirefoxOptions  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

GM_EMAIL = "gm-e2e@test.com"
GM_PASSWORD = "Password1!"  # matches tests.conftest.seed_user
RULESET_ID = "dnd5e"
ADDON_ID = "dice-so-nice-lite"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_http_ready(url: str, *, proc: subprocess.Popen, timeout: float = 30.0) -> None:
    import time

    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return
        except (urllib.error.URLError, ConnectionError, OSError) as err:
            last_err = err
        time.sleep(0.25)
    raise RuntimeError(f"server at {url} not ready in {timeout}s: {last_err}")


def _make_firefox() -> webdriver.Firefox:
    options = FirefoxOptions()
    options.add_argument("-headless")
    return webdriver.Firefox(options=options)


def _seed_database(db_path: Path) -> str:
    """Seed a GM + campaign with dnd5e (ruleset) and dice-so-nice-lite (addon).

    Returns the campaign id. Writes go to ``db_path`` so the subprocess server
    reads the same data.
    """
    import app.persistence.database as db_module
    from app.persistence import engine as engine_module

    db_module.DATABASE_PATH = db_path.resolve()
    db_module._initialized = False
    engine_module.reset_engine()

    from app.business.campaigns.campaign_system_service import CampaignSystemService
    from app.engine.sdk.package_activation_service import PackageActivationService
    from tests.conftest import install_system, seed_campaign, seed_user

    gm_id = seed_user(name="GM", email=GM_EMAIL)
    campaign_id = seed_campaign(gm_id)

    # Ruleset: install + enable + assign to the campaign.
    install_system(gm_id, package_id=RULESET_ID)
    assigned = CampaignSystemService().assign_to_campaign(
        campaign_id=campaign_id, user_id=gm_id, system_id=RULESET_ID
    )
    assert assigned.success, f"assign ruleset failed: {assigned.error_key}"

    # Addon: install + enable + activate for this campaign.
    install_system(gm_id, package_id=ADDON_ID)
    activated = PackageActivationService().activate_package(campaign_id, ADDON_ID, gm_id)
    assert activated.success, f"activate addon failed: {activated.error_key}"

    # Release the SQLite file so the subprocess server can open it cleanly.
    engine_module.reset_engine()
    return campaign_id


@pytest.fixture(scope="module")
def live_table(tmp_path_factory):
    """Boot a real server with a seeded campaign and yield connection details."""
    tmp_dir = tmp_path_factory.mktemp("e2e")
    db_path = tmp_dir / "e2e.sqlite3"
    campaign_id = _seed_database(db_path)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "APP_DEBUG": "true",  # exposes window.GravewrightSDKDebug
            "DATABASE_URL": f"sqlite:///{db_path.resolve().as_posix()}",
            # The allowed-hosts middleware full-matches the Host header including
            # the port; with an ephemeral port a fixed host never matches, so the
            # local test server trusts any host (safe: APP_ENV=test, loopback only).
            "ALLOWED_HOSTS": "*",
            "SESSION_COOKIE_SECURE": "false",
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
        yield {"base_url": base_url, "campaign_id": campaign_id}
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()


@pytest.fixture(scope="module")
def browser():
    try:
        driver = _make_firefox()
    except WebDriverException as err:  # no firefox / geckodriver in this env
        pytest.skip(f"Firefox WebDriver unavailable: {err}")
    driver.set_page_load_timeout(60)
    try:
        yield driver
    finally:
        driver.quit()


def _login(browser: webdriver.Firefox, base_url: str) -> None:
    browser.get(f"{base_url}/login")
    WebDriverWait(browser, 15).until(EC.presence_of_element_located((By.NAME, "email")))
    browser.find_element(By.NAME, "email").send_keys(GM_EMAIL)
    browser.find_element(By.NAME, "password").send_keys(GM_PASSWORD)
    browser.find_element(By.CSS_SELECTOR, "form.auth-form button[type=submit]").click()
    WebDriverWait(browser, 15).until(lambda d: "/login" not in d.current_url)


def test_packages_register_through_sdk_in_real_browser(live_table, browser):
    base_url = live_table["base_url"]
    campaign_id = live_table["campaign_id"]

    _login(browser, base_url)
    browser.get(f"{base_url}/game?room={campaign_id}")

    # The SDK runtime initializes on DOMContentLoaded after every deferred
    # package <script> has had a chance to register; debug is only present when
    # APP_DEBUG is on (it is, for this server).
    WebDriverWait(browser, 30).until(
        lambda d: d.execute_script(
            "return !!(window.GravewrightSDK && window.GravewrightSDKDebug);"
        )
    )

    # The package scripts are themselves loaded async; wait for both runtimes to
    # actually register before snapshotting state.
    WebDriverWait(browser, 30).until(
        lambda d: set(d.execute_script("return window.GravewrightSDKDebug.runtimes();"))
        >= {RULESET_ID, ADDON_ID}
    )

    snapshot = browser.execute_script(
        """
        const dbg = window.GravewrightSDKDebug;
        const caps = window.GravewrightSDKCapabilities;
        const packages = dbg.packages();
        const byId = Object.fromEntries(packages.map(p => [p.id, p]));

        // Capability enforcement must reject undeclared methods and allow declared ones.
        let denied = false, allowed = true;
        try { caps.requireApiCapability({ id: "x", capabilities: [] }, "settings.get"); }
        catch (e) { denied = true; }
        try { caps.requireApiCapability({ id: "x", capabilities: ["settings"] }, "settings.get"); }
        catch (e) { allowed = false; }

        const addon = byId["%(addon)s"] || {};
        const ruleset = byId["%(ruleset)s"] || {};
        return {
            sdkVersion: window.GravewrightSDK.version,
            runtimes: dbg.runtimes(),
            packageIds: packages.map(p => p.id),
            contextDebug: dbg.context().debug,
            contextCampaignId: (dbg.context().campaign || {}).id,
            capsLoaded: !!caps,
            capDenied: denied,
            capAllowed: allowed,
            addonSettingValues: addon.settingValues || {},
            addonSettingDefs: (addon.settingDefinitions || []).length,
            rulesetCapabilities: ruleset.capabilities || [],
            rulesetLocaleKeys: Object.keys(ruleset.locale || {}).length,
        };
        """
        % {"addon": ADDON_ID, "ruleset": RULESET_ID}
    )

    console_text = " ".join(entry.get("message", "") for entry in _browser_log(browser))

    # --- scripts loaded and registered via the SDK ----------------------------
    assert set(snapshot["runtimes"]) >= {RULESET_ID, ADDON_ID}, snapshot
    assert RULESET_ID in snapshot["packageIds"]
    assert ADDON_ID in snapshot["packageIds"]

    # --- debug context wired from APP_DEBUG (item 5) --------------------------
    assert snapshot["contextDebug"] is True
    assert snapshot["contextCampaignId"] == campaign_id

    # --- capability enforcement works in the client ---------------------------
    assert snapshot["capsLoaded"] is True
    assert snapshot["capDenied"] is True, "undeclared capability was not rejected"
    assert snapshot["capAllowed"] is True, "declared capability was wrongly rejected"

    # --- settings payload reaches the client ----------------------------------
    assert snapshot["addonSettingDefs"] >= 1
    assert "dice.color" in snapshot["addonSettingValues"], snapshot["addonSettingValues"]

    # --- locale payload reaches the client ------------------------------------
    assert "locales" in snapshot["rulesetCapabilities"]
    assert snapshot["rulesetLocaleKeys"] >= 1, "ruleset locale dictionary was empty"

    # No SDK-level errors (refused registrations, capability violations) leaked.
    assert "GravewrightSDK" not in console_text or "refused" not in console_text, console_text


def _browser_log(browser: webdriver.Firefox) -> list[dict]:
    """Best-effort browser console log (geckodriver may not expose it)."""
    try:
        return browser.get_log("browser")
    except Exception:
        return []
