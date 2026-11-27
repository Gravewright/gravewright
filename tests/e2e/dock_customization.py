"""Personal dock order, visibility, keyboard access and isolated persistence."""
from __future__ import annotations

import json
import map_builder as harness


def check_browser(base, seed, output, executable, db_snapshot):
    from playwright.sync_api import expect, sync_playwright

    errors, cases = [], []
    game = f"{base}/game/{seed['campaign']}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def ready(current=page):
            current.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
            expect(current.locator('[data-dock-placement="panel:chat"]')).to_have_count(1)

        def settings(current=page):
            current.locator('.game-menubar__logo').click()
            current.locator('.house-menu__section').nth(2).click()
            result = current.locator('[data-dock-settings]')
            expect(result).to_be_visible()
            return result

        def close(current=page):
            current.locator('.house-menu__close').click()

        def row(identifier, current=page):
            return current.locator(f'[data-dock-preference-row="{identifier}"]')

        def order(current=page):
            return current.locator('[data-dock-primary] > button').evaluate_all('rows=>rows.map(row=>row.dataset.dockEntry)')

        try:
            page.goto(game); ready()
            original = order()
            settings()
            row('panel:chat').locator('[data-dock-move=down]').click()
            assert order().index('panel:actors') < order().index('panel:chat')
            expect(row('panel:chat').locator('[data-dock-move=down]')).to_be_focused()
            row('panel:scenes').locator('select').select_option('dock')
            expect(page.locator('[data-dock-primary] [data-panel=scenes]')).to_have_count(1)
            row('panel:chat').locator('select').select_option('hidden')
            tool_group = page.locator('.dock-preference-group').filter(has=row('tool:game:measure'))
            tool_group.locator('summary').click()
            row('tool:game:measure').locator('[data-dock-move=up]').click()
            assert page.locator('[data-shortcut-layer=game] > button').first.get_attribute('data-dock-tool') == 'measure'
            row('tool:game:measure').locator('select').select_option('hidden')
            close()
            expect(page.locator('.game-dock [data-panel=chat]')).to_be_hidden()
            page.keyboard.press('c')
            expect(page.locator('#chat-panel')).to_be_visible()
            page.keyboard.press('c')
            page.keyboard.press('r')
            expect(page.locator('[data-shortcut-layer=game] [data-dock-tool=measure]')).to_have_attribute('aria-pressed', 'true')
            page.locator('[data-dock-primary] [data-panel=scenes]').click()
            expect(page.locator('#maps-panel')).to_be_visible()
            page.keyboard.press('m')
            cases.append('Order, pinning, hidden controls, real actions and preserved shortcuts')

            page.reload(); ready(); settings()
            expect(row('panel:chat').locator('select')).to_have_value('hidden')
            expect(row('panel:scenes').locator('select')).to_have_value('dock')
            twin = context.new_page(); twin.goto(game); ready(twin)
            expect(twin.locator('.game-dock [data-panel=chat]')).to_be_hidden()
            page.locator('[data-dock-reset]').click()
            expect(twin.locator('.game-dock [data-panel=chat]')).to_be_visible()
            assert order() == original
            twin.close()
            cases.append('Reload, shared-tab synchronization and complete default restoration')

            page.evaluate('''() => { window.restoreDockStorage = Storage.prototype.setItem;
                Storage.prototype.setItem = () => { throw new DOMException('Blocked', 'QuotaExceededError'); }; }''')
            row('panel:chat').locator('select').select_option('hidden')
            expect(page.locator('[data-dock-settings-error]')).to_be_visible()
            expect(row('panel:chat').locator('select')).to_have_value('dock')
            page.evaluate('() => { Storage.prototype.setItem = window.restoreDockStorage; }')
            page.locator('[data-dock-reset]').click()
            cases.append('Storage failures keep the last saved layout and report an error')

            for locale, title in [('en', 'Customize the dock'), ('pt-BR', 'Personalizar a dock'), ('es', 'Personalizar el dock')]:
                close()
                harness.change_locale(page, locale, seed['campaign'])
                page.reload(); ready(); settings()
                expect(page.locator('[data-dock-settings] > header > strong')).to_have_text(title)
                for width in (1440, 390, 320):
                    page.set_viewport_size({'width': width, 'height': 844})
                    page.locator('[data-dock-settings]').scroll_into_view_if_needed()
                    metrics = page.locator('[data-dock-settings]').evaluate('''root=>({
                        overflow:root.scrollWidth>root.clientWidth,
                        tiny:[...root.querySelectorAll('label,select,button,p,summary')].some(node=>
                            node.getClientRects().length && parseFloat(getComputedStyle(node).fontSize)<12),
                        left:root.getBoundingClientRect().left,right:root.getBoundingClientRect().right})''')
                    assert not metrics['overflow'] and not metrics['tiny'], metrics
                    assert metrics['left'] >= 0 and metrics['right'] <= width, metrics
                    page.screenshot(path=str(output / f'dock-settings-{locale}-{width}.png'))
                page.set_viewport_size({'width': 1440, 'height': 900})
            cases.append('English, Portuguese and Spanish at 1440, 390 and 320 pixels')

            # Put every available panel in the main dock and verify that it wraps.
            for select in page.locator('[data-dock-preference-row^="panel:"]:visible select').all():
                select.select_option('dock')
            close()
            page.set_viewport_size({'width': 320, 'height': 844})
            bounds = page.locator('.game-dock').bounding_box()
            assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= 320, bounds
            page.screenshot(path=str(output / 'dock-all-panels-320.png'))
            page.locator('[data-dock-menu-toggle]').click()
            expect(page.locator('[data-dock-menu-empty]')).to_be_visible()
            page.screenshot(path=str(output / 'dock-empty-menu-320.png'))
            page.locator('[data-dock-menu-toggle]').click()
            settings(); page.locator('[data-dock-reset]').click()
            row('panel:chat').locator('select').select_option('hidden')
            close()

            # The same browser storage must not transfer the GM's choices to a player.
            context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            page.goto(game); ready()
            expect(page.locator('.game-dock [data-panel=chat]')).to_be_visible()
            settings()
            expect(row('panel:chat').locator('select')).to_have_value('dock')
            expect(row('panel:scenes')).to_have_count(0)
            expect(page.locator('[data-dock-preference-row^="tool:walls:"]')).to_have_count(0)
            cases.append('Many pinned panels remain usable at 320 pixels; profiles and GM controls stay isolated')
            assert not errors, errors
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'diagnostics.json').write_text(json.dumps({'cases': cases, 'errors': errors}, indent=2))
            raise
        finally:
            context.close(); browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
