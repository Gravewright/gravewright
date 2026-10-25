"""Split a party between scenes and show saved player colors in the directory."""
from migration_closure import main
from playwright.sync_api import expect


SEED = """
from gravewright.accounts.models import UserPreference
UserPreference.objects.create(user=player,ping_color='#11aa55')
second=User.objects.create_user('second@example.test','password-123',name='Second player with a longer display name')
membership=Membership.objects.create(campaign=c,user=second)
Onboarding.objects.create(membership=membership,dismissed=True,player_shown_at=timezone.now())
UserPreference.objects.create(user=second,ping_color='#ff8800')
client=Client();client.force_login(second)
result['second']=client.session.session_key
result['second_id']=str(second.pk)
"""


def check(gm, player, data, output):
    base = gm.url.split('/game/')[0]
    ctx = gm.context.browser.new_context(viewport={'width': 1440, 'height': 1000})
    ctx.add_cookies([{'name': data['cookie'], 'value': data['second'], 'url': base}])
    second = ctx.new_page()
    errors = []
    second.on('pageerror', lambda error: errors.append(str(error)))
    try:
        second.goto(gm.url)
        second.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=data['map'])

        def current(page, scene_id):
            page.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=scene_id)

        def row(scene_id):
            return gm.locator(f'#maps-panel [data-scene-id="{scene_id}"]')

        def create(name):
            result = gm.evaluate('''async p => {
                const {HttpClient}=await import('/static/gravewright_modules/http-client.js');
                return new HttpClient().post('/api/containers/'+p.campaign+'/scene-empty',{
                    requestId:crypto.randomUUID(),name:p.name,width:700,height:700,
                    color:'#354b66',gridVisible:true,activate:false});
            }''', {**data, 'name': name})
            current(gm, result['id'])
            return result['id']

        def assign(scene_id, names):
            row(scene_id).click(button='right')
            gm.get_by_role('menuitem', name='Activate for selected players', exact=True).click()
            modal = gm.get_by_role('dialog', name='Activate for selected players', exact=True)
            expect(modal.get_by_role('button', name='Activate', exact=True)).to_be_disabled()
            for name in names:
                modal.get_by_role('checkbox', name=name, exact=True).check()
            gm.screenshot(path=str(output / f'scene-audience-select-{len(names)}.png'))
            modal.get_by_role('button', name='Activate', exact=True).click()
            expect(modal).to_have_count(0)

        first = data['map']
        split = create('Separate party')
        gm.evaluate('gravewrightMaps.showDirectory()')
        expect(row(first).locator('.game-scene-player-dot')).to_have_count(2)
        expect(row(split).locator('.game-scene-gm')).to_have_text('GM')
        expect(row(first).locator(f'[data-player-id="{data["player_id"]}"]')).to_have_css('background-color', 'rgb(17, 170, 85)')
        assign(split, ['Player'])
        current(player, split)
        current(second, first)
        expect(row(split).locator('.game-scene-player-dot')).to_have_count(1)
        expect(row(first).locator('.game-scene-player-dot')).to_have_count(1)
        assert second.request.get(base + f'/api/maps/{split}/manifest').status == 404
        assert player.request.get(base + f'/api/maps/{first}/manifest').status == 404
        gm.screenshot(path=str(output / 'scene-audience-split-desktop.png'))

        together = create('Gather the selected players')
        gm.set_viewport_size({'width': 390, 'height': 844})
        gm.evaluate('gravewrightMaps.showDirectory()')
        assign(together, ['Player', 'Second player with a longer display name'])
        for page in (player, second):
            current(page, together)
        expect(row(together).locator('.game-scene-player-dot')).to_have_count(2)
        second.evaluate('''async () => {
            const {HttpClient}=await import('/static/gravewright_modules/http-client.js');
            await new HttpClient().post('/api/player-preferences',{pingColor:'#cc0044'});
        }''')
        expect(row(together).locator(f'[data-player-id="{data["second_id"]}"]')).to_have_css('background-color', 'rgb(204, 0, 68)')
        player.reload()
        current(player, together)
        gm.screenshot(path=str(output / 'scene-audience-split-mobile.png'))

        row(first).click(button='right')
        gm.get_by_role('menuitem', name='Activate for players', exact=True).click()
        for page in (gm, player, second):
            current(page, first)
        expect(row(first).locator('.game-scene-player-dot')).to_have_count(2)
        expect(row(together).locator('.game-scene-player-dot')).to_have_count(0)
        # Let tile FileResponses finish before the Windows fixture removes media.
        for page in (gm, player, second):
            page.wait_for_load_state('networkidle')
        assert not errors, errors
        print('Scene audiences: single/multiple recipients, color dots, live color changes, reload, access isolation and table reunion passed', flush=True)
    finally:
        ctx.close()


if __name__ == '__main__':
    main(check, seed_extra=SEED)
