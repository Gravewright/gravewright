from __future__ import annotations

from playwright.sync_api import BrowserContext, Page, expect, sync_playwright

from tests.e2e.test_app_server_e2e import (
    CAMPAIGN_TITLE,
    GM_EMAIL,
    GM_PASSWORD,
    PLAYER_EMAIL,
    PLAYER_PASSWORD,
)

pytest_plugins = ["tests.e2e.test_app_server_e2e"]


def _login(page: Page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)
    page.locator('button[type="submit"]').click()
    page.wait_for_url(f"{base_url}/inside")


def _csrf(page: Page) -> str:
    return page.evaluate("window.csrfToken?.() || ''")


def _permission_modal_status(page: Page, base_url: str, kind: str, resource_id: str) -> int:
    return page.evaluate(
        """async ({url}) => (await fetch(url, {credentials: 'same-origin'})).status""",
        {"url": f"{base_url}/game/resource-permissions/{kind}/{resource_id}"},
    )


def _close(context: BrowserContext) -> None:
    try:
        context.close()
    except Exception:
        pass


def test_gm_and_player_first_visit_permissions_and_live_ban(live_server) -> None:
    base_url = live_server["base_url"]
    campaign_id = live_server["campaign_id"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        gm_context = browser.new_context()
        player_context = browser.new_context()
        try:
            gm = gm_context.new_page()
            player = player_context.new_page()
            _login(gm, base_url, GM_EMAIL, GM_PASSWORD)
            _login(player, base_url, PLAYER_EMAIL, PLAYER_PASSWORD)

            gm.goto(f"{base_url}/game?room={campaign_id}")
            player.goto(f"{base_url}/game?room={campaign_id}")
            expect(player.locator(f'[data-modal-id="settings-interface-{campaign_id}"]')).to_be_visible()

            # The introduction is persisted server-side and does not reopen on reload.
            player.reload()
            expect(player.locator(f'[data-modal-id="settings-interface-{campaign_id}"]')).to_be_hidden()
            player.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")

            # Switching tables gets its own first-visit state; returning to the
            # original table keeps the persisted state and reconnects realtime.
            second_campaign_id = live_server["second_campaign_id"]
            player.goto(f"{base_url}/game?room={second_campaign_id}")
            expect(player.locator(f'[data-modal-id="settings-interface-{second_campaign_id}"]')).to_be_visible()
            player.goto(f"{base_url}/game?room={campaign_id}")
            expect(player.locator(f'[data-modal-id="settings-interface-{campaign_id}"]')).to_be_hidden()
            player.wait_for_function("window.GravewrightRealtime?.isOpen?.() === true")

            # GM can load the same permissions model for every supported resource.
            for kind in ("actor", "item", "journal"):
                resource_id = live_server[f"{kind}_id"]
                assert _permission_modal_status(
                    gm, base_url, kind, resource_id
                ) == 200
                saved = gm.evaluate(
                    """async ({kind, resourceId, playerId, csrf}) => {
                        const body = new URLSearchParams({resource_type: kind, resource_id: resourceId});
                        body.set(`access__${playerId}`, 'read');
                        const result = await fetch('/game/resource-permissions', {
                            method: 'POST', credentials: 'same-origin',
                            headers: {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', 'x-csrftoken': csrf}, body,
                        });
                        return result.status;
                    }""",
                    {"kind": kind, "resourceId": resource_id, "playerId": live_server["player_id"], "csrf": _csrf(gm)},
                )
                assert saved == 200

            # Mission updates cross the real HTTP + realtime path.
            player.evaluate(
                """window.__questUpdated = false;
                document.addEventListener('vtt:transport-event', (event) => {
                    if (event.detail?.event === 'quest.status_changed') window.__questUpdated = true;
                });"""
            )
            quest_response = gm.evaluate(
                """async ({questId, csrf}) => {
                    const body = new URLSearchParams({journal_id: questId, status: 'in_progress'});
                    const result = await fetch('/game/journal/quest/status', {
                        method: 'POST', credentials: 'same-origin',
                        headers: {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', 'x-csrftoken': csrf}, body,
                    });
                    return result.status;
                }""",
                {"questId": live_server["quest_id"], "csrf": _csrf(gm)},
            )
            assert quest_response == 200
            player.wait_for_function("window.__questUpdated === true")

            # The live player is removed immediately when the GM bans the account.
            response = gm.evaluate(
                """async ({campaignId, userId, csrf}) => {
                    const body = new URLSearchParams({campaign_id: campaignId, user_id: userId});
                    const result = await fetch('/game/member/ban', {
                        method: 'POST', credentials: 'same-origin',
                        headers: {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', 'x-csrftoken': csrf},
                        body,
                    });
                    return {status: result.status, payload: await result.json()};
                }""",
                {
                    "campaignId": campaign_id,
                    "userId": live_server["player_id"],
                    "csrf": _csrf(gm),
                },
            )
            assert response["status"] == 200 and response["payload"]["ok"] is True
            player.wait_for_url(f"{base_url}/inside", timeout=10_000)
            expect(player.get_by_text(CAMPAIGN_TITLE)).to_have_count(0)
        finally:
            _close(player_context)
            _close(gm_context)
            browser.close()
