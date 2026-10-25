"""Shared scene pointers: named peers, smooth movement and scene isolation."""
from migration_closure import main
from playwright.sync_api import expect


SEED = """
from gravewright.accounts.models import UserPreference
UserPreference.objects.create(user=owner,ping_color='#129abc')
UserPreference.objects.create(user=player,ping_color='#a1b2c3')
"""


def check(gm, player, data, output):
    gm_id = gm.locator('#table-workspace').get_attribute('data-profile-id')
    player_id = data['player_id']
    for page in (gm, player):
        page.evaluate('''() => {
            window.cursorPackets=[];
            addEventListener('gravewright:map-cursor', ({detail}) => cursorPackets.push(detail));
        }''')

    def peer(page, user_id):
        return page.locator(f'[data-map-pointer="{user_id}"]')

    # Playwright normally emulates focus on every page. Disable that behavior
    # to exercise real account-window switching and its blur/visibility events.
    sessions = [page.context.new_cdp_session(page) for page in (gm, player)]
    for session in sessions:
        session.send('Emulation.setFocusEmulationEnabled', {'enabled': False})
    try:
        player.bring_to_front()
        player.mouse.move(600, 350)
        expect(peer(gm, player_id)).to_be_visible()
        gm.bring_to_front()
        gm.wait_for_timeout(300)
        expect(peer(gm, player_id)).to_be_visible()
        gm.screenshot(path=str(output / 'player-pointer-after-switching-account.png'))
        gm.mouse.move(650, 300)
        expect(peer(player, gm_id)).to_be_visible()
        player.bring_to_front()
        player.wait_for_timeout(300)
        expect(peer(player, gm_id)).to_be_visible()
        player.screenshot(path=str(output / 'gm-pointer-after-switching-account.png'))
        # Switch away before the throttled move is published. A cancelled
        # timeout must not fire later and turn a pause into a hide packet.
        player.evaluate('''() => {
            document.querySelector('.game-board__surface').dispatchEvent(new PointerEvent('pointermove',
              {bubbles:true,pointerType:'mouse',clientX:610,clientY:350}));
            window.dispatchEvent(new Event('blur'));
        }''')
        player.wait_for_timeout(200)
        expect(peer(gm, player_id)).to_be_visible()
        # Moving to browser chrome has no related DOM target. It suspends the
        # publisher while retaining the last shared scene position.
        player.locator('.game-table__scene-frame').dispatch_event('pointerleave', {'relatedTarget': None})
        player.evaluate('window.dispatchEvent(new Event("blur"))')
        player.wait_for_timeout(200)
        expect(peer(gm, player_id)).to_be_visible()
        # Chromium's automation flags can keep background tabs visible, so
        # exercise the hidden-document branch explicitly as well as real blur.
        try:
            player.evaluate('''() => {
                Object.defineProperty(document,'hidden',{configurable:true,value:true});
                document.dispatchEvent(new Event('visibilitychange'));
            }''')
            player.wait_for_timeout(200)
            expect(peer(gm, player_id)).to_be_visible()
        finally:
            player.evaluate('delete document.hidden')
    finally:
        for session in sessions:
            session.send('Emulation.setFocusEmulationEnabled', {'enabled': True})
            session.detach()

    gm.mouse.move(650, 300)
    expect(peer(player, gm_id)).to_be_visible()
    expect(peer(player, gm_id).locator('.map-pointer__name')).to_have_text('GM')
    expect(peer(player, gm_id).locator('.map-pointer__dot')).to_have_css('background-color', 'rgb(18, 154, 188)')
    expect(peer(gm, gm_id)).to_have_count(0)
    player.mouse.move(500, 350)
    expect(peer(gm, player_id)).to_be_visible()
    expect(peer(gm, player_id).locator('.map-pointer__name')).to_have_text('Player')
    expect(peer(gm, player_id).locator('.map-pointer__dot')).to_have_css('background-color', 'rgb(161, 178, 195)')
    expect(peer(player, player_id)).to_have_count(0)
    # Tools receive mouse events on overlays beside the rendering surface.
    # Moving onto them must keep publishing the pointer, including drags.
    player.get_by_role('button', name='Measure', exact=True).click()
    player.mouse.move(550, 320)
    expect(player.locator('.measurement-workspace--active')).to_be_visible()
    gm.wait_for_function('''id => {
        const node=document.querySelector('[data-map-pointer="'+id+'"]');
        return node && !node.hidden && Math.abs(node.getBoundingClientRect().x-550)<1;
    }''', arg=player_id)
    player.mouse.down()
    player.mouse.move(580, 340, steps=5)
    player.mouse.up()
    expect(peer(gm, player_id)).to_be_visible()
    gm.evaluate('window.cursorPackets.length=0')
    player.get_by_role('button', name='Close measurement', exact=True).click()
    player.mouse.move(550, 320)
    # Wait for the new position to reach the other account before pausing the
    # publisher; the close-button hide packet can still be in flight.
    gm.wait_for_function('''id => {
        const packet=window.cursorPackets.at(-1);
        return packet?.userId===id && packet.position?.x===550 && packet.position?.y===320;
    }''', arg=player_id)
    expect(peer(gm, player_id)).to_be_visible()
    # A delayed packet is not a departure: pause only publication while the
    # socket remains seated, and let the old short expiry window elapse.
    player.evaluate('''() => {
        window.originalMapCursor=gravewrightRealtime.mapCursor;
        gravewrightRealtime.mapCursor=()=>true;
    }''')
    gm.wait_for_timeout(5500)
    expect(peer(gm, player_id)).to_be_visible()
    player.evaluate('() => { gravewrightRealtime.mapCursor=window.originalMapCursor; }')
    player.mouse.move(500, 350)
    # Scene overlays can be siblings of the renderer surface. Publish their
    # coordinates while retaining the native control/window exclusions.
    player.evaluate('''() => {
        const overlay=document.createElement('div');overlay.id='pointer-test-overlay';
        overlay.style.cssText='position:absolute;inset:0;z-index:20';
        document.querySelector('.game-board').append(overlay);
    }''')
    player.mouse.move(600, 370)
    gm.wait_for_function('''id => {
        const node=document.querySelector('[data-map-pointer="'+id+'"]');
        return node && !node.hidden && Math.abs(node.getBoundingClientRect().x-600)<1;
    }''', arg=player_id)
    player.locator('#pointer-test-overlay').evaluate('node=>node.remove()')
    player.mouse.move(500, 350)
    gm.evaluate('''id => {
        window.pointerMotion=[];
        const start=performance.now();
        function sample(now) {
            const marker=document.querySelector('[data-map-pointer="'+id+'"]');
            if(marker) pointerMotion.push(marker.getBoundingClientRect().x);
            if(now-start<800) requestAnimationFrame(sample);
        }
        requestAnimationFrame(sample);
    }''', player_id)
    player.mouse.move(700, 400)
    gm.wait_for_function('''id => {
        const rect=document.querySelector('[data-map-pointer="'+id+'"]').getBoundingClientRect();
        return Math.abs(rect.x-700)<1 && Math.abs(rect.y-400)<1;
    }''', arg=player_id)
    assert gm.evaluate('pointerMotion.some(x=>x>501 && x<699)'), 'Peer movement must interpolate between network positions.'
    point = player.evaluate('gravewrightMaps.board.worldAt({x:700,y:400})')
    scale = gm.evaluate('gravewrightMaps.board.viewport().scale')
    gm.mouse.move(500, 450)
    gm.mouse.wheel(0, -240)
    gm.wait_for_function('scale => gravewrightMaps.board.viewport().scale !== scale', arg=scale)
    gm.wait_for_function('''p => {
        const rect=document.querySelector('[data-map-pointer="'+p.id+'"]').getBoundingClientRect();
        const bounds=document.querySelector('.game-board__surface').getBoundingClientRect();
        const view=gravewrightMaps.board.viewport();
        return Math.abs(rect.x-bounds.x-view.x-p.point.x*view.scale)<1
            && Math.abs(rect.y-bounds.y-view.y-p.point.y*view.scale)<1;
    }''', arg={'id': player_id, 'point': point})
    gm.screenshot(path=str(output / 'shared-pointer-name-color-zoom.png'))

    player.mouse.move(20, 15)
    expect(peer(gm, player_id)).to_have_count(0)
    player.locator('.game-menubar__logo').click()
    player.locator('.house-menu__section').nth(2).click()
    color = player.get_by_label('Identification color', exact=True)
    expect(color).to_be_enabled()
    with player.expect_response(lambda response: response.url.endswith('/api/player-preferences') and response.request.method == 'POST') as response:
        color.evaluate('''el => {
            el.value='#ee2266'; el.dispatchEvent(new Event('change',{bubbles:true}));
        }''')
    assert response.value.ok
    expect(color).to_be_enabled()
    player.locator('.house-menu__close').click()
    player.mouse.move(600, 300)
    expect(peer(gm, player_id).locator('.map-pointer__dot')).to_have_css('background-color', 'rgb(238, 34, 102)')
    player.reload()
    player.wait_for_function('!!gravewrightMaps.board?.viewport()')
    player.mouse.move(650, 330)
    expect(peer(gm, player_id).locator('.map-pointer__dot')).to_have_css('background-color', 'rgb(238, 34, 102)')
    player.locator('.game-board__surface').dispatch_event('pointermove', {'pointerType':'touch','clientX':650,'clientY':330})
    expect(peer(gm, player_id)).to_have_count(0)

    gm.get_by_role('group', name='Layers', exact=True).get_by_role('button', name='GM', exact=True).click()
    expect(peer(player, gm_id)).to_have_count(0)
    gm.mouse.move(600, 300)
    expect(peer(player, gm_id)).to_have_count(0)
    scene = gm.evaluate('''async campaign => {
        const {HttpClient}=await import('/static/gravewright_modules/http-client.js');
        return new HttpClient().post('/api/containers/'+campaign+'/scene-empty', {
            requestId:crypto.randomUUID(),name:'Private pointer test',color:'#354b66',
            width:700,height:700,gridVisible:true,activate:false});
    }''', data['campaign'])
    gm.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=scene['id'])
    gm.evaluate('id => gravewrightRealtime.mapCursor({mapId:id,position:{x:100,y:100}})', scene['id'])
    assert player.request.get(gm.url.split('/game/')[0]+f'/api/maps/{scene["id"]}/manifest').status == 404
    player.wait_for_timeout(200)
    assert player.evaluate('id => !(window.cursorPackets||[]).some(p=>p.mapId===id)', scene['id'])
    gm.evaluate('gravewrightMaps.showDirectory()')
    row = gm.locator(f'#maps-panel [data-scene-id="{scene["id"]}"]')
    expect(row.locator('.game-scene-gm')).to_have_text('GM')
    expect(gm.locator('#maps-panel [data-navigating]')).to_have_count(0)
    gm.evaluate('gravewrightRealtime.mapCommand("navigate",{mapId:null})')
    gm.wait_for_function('id => gravewrightMaps.current?.id === id', arg=data['map'])
    player.mouse.move(600, 300)
    expect(peer(gm, player_id)).to_be_visible()
    player.evaluate('sockets.at(-1).close(4401)')
    expect(peer(gm, player_id)).to_have_count(0)
    print('Shared pointers: real account-window focus changes, browser chrome, overlays, measurement drags, delayed updates, native self cursor, peer names/colors, movement, zoom, live color, reload, leave, touch, private scenes/layers and disconnect passed', flush=True)


if __name__ == '__main__':
    main(check, seed_extra=SEED)
