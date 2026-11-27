"""Dock scene actions reach authorized GM/player/streamer clients over realtime."""
import json
import time

import map_builder as harness


def check_browser(base, seed, output, executable, db_snapshot):
    from playwright.sync_api import expect, sync_playwright
    errors, timings = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        pages, contexts = {}, []
        try:
            for role in ('gm', 'player', 'streamer'):
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                contexts.append(context)
                context.add_cookies([{**seed['sessions'][role], 'url': base}])
                context.add_init_script('''window.receivedFrames=[];
                    const Native=WebSocket;window.WebSocket=class extends Native {
                    constructor(...args){super(...args);this.addEventListener('message',event=>window.receivedFrames.push(event.data));}};''')
                page = pages[role] = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f"{base}/game/{seed['campaign']}")
                page.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
            gm, player, streamer = (pages[role] for role in ('gm', 'player', 'streamer'))
            gm.evaluate('(mapId)=>gravewrightRealtime.mapCommand("navigate",{mapId})', seed['broadcastScene'])
            gm.wait_for_function('(id)=>gravewrightMaps.current?.id===id', arg=seed['broadcastScene'])

            def wait_state(page, predicate):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    state = page.evaluate('async id=>(await (await fetch(`/api/maps/${id}/state`)).json())', seed['broadcastScene'])
                    if predicate(state):
                        return state
                    page.wait_for_timeout(25)
                raise AssertionError(f'Scene state did not reach the expected committed state: {state}')

            def measure(page, title, x=430, y=330):
                page.locator('.game-dock__group:visible [data-dock-tool=measure]').click()
                panel = page.locator('.measure-panel')
                panel.get_by_label('Title', exact=True).check()
                page.mouse.move(x, y); page.mouse.down()
                page.mouse.move(x + 140, y + 100, steps=4); page.mouse.up()
                textbox = page.get_by_role('textbox', name='Measurement title', exact=True).last
                textbox.fill(title); textbox.press('Enter')
                return panel

            started = time.perf_counter()
            panel = measure(gm, 'Public GM measurement <script>')
            for recipient in (player, streamer):
                expect(recipient.locator('.measurement-title__text')).to_have_text('Public GM measurement <script>')
            timings.append({'action': 'GM measurement including title and player/streamer delivery',
                            'milliseconds': (time.perf_counter() - started) * 1000})
            panel.get_by_role('button', name='Close measurement', exact=True).click()
            panel = measure(player, 'Player measurement', x=650, y=380)
            expect(gm.locator('.measurement-title__text')).to_have_count(2)
            expect(streamer.locator('.measurement-title__text')).to_have_count(2)
            expect(player.get_by_role('textbox', name='Measurement title', exact=True).first).to_be_disabled()
            panel.get_by_role('button', name='Close measurement', exact=True).click()

            markers = wait_state(player, lambda state: len(state['markers']) == 2)['markers']
            own = next(row for row in markers if row['title'] == 'Player measurement')
            foreign = next(row for row in markers if row['title'] == 'Public GM measurement <script>')
            assert own['canEdit'] is True and foreign['canEdit'] is False
            player.locator('.game-dock__group:visible [data-dock-tool=select]').click()
            player.keyboard.press('Control+a')
            # Measurements use their dedicated editor, outside general selection layers.
            for marker in (own, foreign):
                expect(player.locator(f'[data-selected-object="measure:{marker["id"]}"]')).to_have_count(0)
            player.keyboard.press('Escape')

            gm.locator('[data-menubar-shortcut=layer-gm]').click()
            panel = measure(gm, 'GM SECRET measurement', x=800, y=450)
            wait_state(gm, lambda state: any(row['title'] == 'GM SECRET measurement' for row in state['markers']))
            # A new subscription forces a complete server projection, including privacy filtering.
            for recipient in (player, streamer):
                recipient.evaluate('id=>gravewrightRealtime.mapLayers(id)', seed['broadcastScene'])
                expect(recipient.locator('.measurement-title__text')).to_have_count(2)
            panel.get_by_role('button', name='Close measurement', exact=True).click()
            gm.reload(); gm.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
            expect(gm.locator('.measurement-title__text')).to_have_count(3)

            # Mini Paint uses the same committed, recipient-filtered scene transport.
            gm.locator('[data-menubar-shortcut=layer-game]').click()
            gm.locator('.game-dock__group:visible [data-dock-tool=draw]').click()
            gm.mouse.move(400, 500); gm.mouse.down(); gm.mouse.move(580, 540, steps=4); gm.mouse.up()
            wait_state(gm, lambda state: len(state['drawings']['rows']) == 1)
            for recipient in (player, streamer):
                recipient.wait_for_function('''()=>receivedFrames.some(frame=>{try{const p=JSON.parse(frame).payload;return p?.drawings?.rows?.length===1;}catch{return false;}})''')
            gm.locator('.drawing-paint').get_by_role('button', name='Close drawing').click()
            gm.locator('[data-menubar-shortcut=layer-gm]').click()
            gm.locator('.game-dock__group:visible [data-dock-tool=draw]').click()
            gm.mouse.move(700, 500); gm.mouse.down(); gm.mouse.move(880, 540, steps=4); gm.mouse.up()
            wait_state(gm, lambda state: len(state['drawings']['rows']) == 2)
            for recipient in (player, streamer):
                state = recipient.evaluate('async id=>(await (await fetch(`/api/maps/${id}/state`)).json())', seed['broadcastScene'])
                assert len(state['drawings']['rows']) == 1
                assert len(state['markers']) == 2
                assert not recipient.evaluate("receivedFrames.some(frame=>frame.includes('GM SECRET measurement'))")
            expect(player.locator('[data-shortcut-layer=gm]')).to_have_count(0)
            expect(streamer.locator('[data-dock-tool=measure]')).to_have_count(0)
            gm.screenshot(path=str(output / 'gm-shared-private.png'))
            player.screenshot(path=str(output / 'player-shared.png'))
            streamer.screenshot(path=str(output / 'streamer-readonly.png'))
            assert not errors, errors
        except Exception:
            for role, page in pages.items():
                page.screenshot(path=str(output / f'failure-{role}.png'))
            (output / 'diagnostics.json').write_text(json.dumps({'pageErrors': errors, 'timings': timings}, indent=2))
            raise
        finally:
            for context in contexts: context.close()
            browser.close()
    return {'passed': True, 'pageErrors': errors, 'timings': timings,
            'cases': ['GM/player measurements and titles broadcast; streamer receives read-only',
                      'Measurements use the dedicated editor and preserve ownership outside general selection',
                      'GM-private measurements absent from player/streamer packets',
                      'Measurements survive reload; Mini Paint shares only public drawings']}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
