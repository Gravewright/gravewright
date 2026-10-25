"""Personal pointer visibility and sharing controls with two isolated accounts."""
from playwright.sync_api import expect

from map_builder import MEASURE
from map_pointer import SEED as POINTER_SEED
from migration_closure import main


SEED = POINTER_SEED + """
from zipfile import ZipFile
from gravewright.modules.packages import host
manifest={'id':'gravewright.translator','version':'0.1.0',
    'name':'Synthetic pointer preference languages','description':'Disposable browser fixture',
    'author':'Gravewright tests','license':'MIT','entry':'main.js',
    'sdk':{'requires':'>=1.0.0 <2.0.0','tested':'1.0.0'},
    'locales':{'pt-BR':{'name':'Portuguese','path':'locales/pt-BR.json'}}}
archive_data=BytesIO()
with ZipFile(archive_data,'w') as archive:
    archive.writestr('manifest.json',json.dumps(manifest))
    archive.writestr('main.js','export default {start(){},stop(){}};')
    archive.writestr('locales/pt-BR.json',json.dumps({'Close':'Fechar'}))
host().install_local(archive_data.getvalue(),expected_type='module')
language_client=Client();language_client.force_login(owner)
activated=language_client.post('/api/module-packages/activation',{
    'id':manifest['id'],'version':manifest['version'],'enabled':True},content_type='application/json')
assert activated.status_code==200,activated.content
"""


def environment(temp):
    return {'GRAVEWRIGHT_MODULES_ROOT': temp + '/modules',
            'GRAVEWRIGHT_CONTENT_ROOT': temp + '/content',
            'GRAVEWRIGHT_DJANGO_REGISTRY': temp + '/modules/server-apps.json'}


def check(gm, player, data, output):
    gm_id = gm.locator('#table-workspace').get_attribute('data-profile-id')
    player_id = data['player_id']

    def peer(page, identifier):
        return page.locator(f'[data-map-pointer="{identifier}"]')

    def preferences(page):
        page.locator('.game-menubar__logo').click()
        page.locator('.house-menu__section').nth(2).click()
        group = page.locator('[data-table-pointers]')
        expect(group).to_be_visible()
        return group

    def close(page):
        page.locator('.house-menu__close').click()

    gm.mouse.move(650, 300)
    player.mouse.move(600, 350)
    expect(peer(gm, player_id)).to_be_visible()
    expect(peer(player, gm_id)).to_be_visible()
    options = preferences(gm)
    view = options.locator('[data-map-pointer-visibility]')
    share = options.locator('[data-map-pointer-sharing]')
    expect(view).to_be_checked()
    expect(share).to_be_checked()
    view.uncheck()
    expect(peer(gm, player_id)).not_to_be_visible()
    close(gm)
    gm.mouse.move(650, 300)
    expect(peer(player, gm_id)).to_be_visible()
    player.mouse.move(620, 360)
    expect(peer(gm, player_id)).not_to_be_visible()
    options = preferences(gm)
    options.locator('[data-map-pointer-visibility]').check()
    expect(peer(gm, player_id)).to_be_visible()
    gm.screenshot(path=str(output / 'pointer-preferences-enabled.png'))
    options.locator('[data-map-pointer-visibility]').uncheck()
    close(gm)
    gm.reload()
    gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    options = preferences(gm)
    expect(options.locator('[data-map-pointer-visibility]')).not_to_be_checked()
    expect(options.locator('[data-map-pointer-sharing]')).to_be_checked()
    player.mouse.move(630, 370)
    expect(peer(gm, player_id)).not_to_be_visible()
    options.locator('[data-map-pointer-visibility]').check()
    expect(peer(gm, player_id)).to_be_visible()
    close(gm)

    options = preferences(player)
    expect(options.locator('[data-map-pointer-visibility]')).to_be_checked()
    options.locator('[data-map-pointer-sharing]').uncheck()
    expect(peer(gm, player_id)).to_have_count(0)
    close(player)
    player.mouse.move(600, 350)
    player.wait_for_timeout(1200)
    expect(peer(gm, player_id)).to_have_count(0)
    gm.mouse.move(670, 310)
    expect(peer(player, gm_id)).to_be_visible()
    player.reload()
    player.wait_for_function('!!gravewrightMaps.board?.viewport()')
    player.mouse.move(640, 380)
    player.wait_for_timeout(200)
    expect(peer(gm, player_id)).to_have_count(0)
    options = preferences(player)
    expect(options.locator('[data-map-pointer-sharing]')).not_to_be_checked()
    expect(options.locator('[data-map-pointer-visibility]')).to_be_checked()
    options.locator('[data-map-pointer-sharing]').check()
    close(player)
    player.mouse.move(650, 390)
    expect(peer(gm, player_id)).to_be_visible()

    # A failed device write must keep the actual setting and report the error.
    options = preferences(player)
    player.evaluate('''() => {
      window.savedStorageWrite=Storage.prototype.setItem;
      Storage.prototype.setItem=()=>{throw new DOMException('Fixture storage is blocked','SecurityError')};
    }''')
    try:
        options.locator('[data-map-pointer-sharing]').click()
        expect(options.locator('[data-map-pointer-sharing]')).to_be_checked()
        expect(options.locator('[data-map-pointer-preference-error]')).to_be_visible()
    finally:
        player.evaluate('() => { Storage.prototype.setItem=window.savedStorageWrite; }')
    close(player)

    # Native language changes verify the existing translation mechanism.
    options = preferences(player)
    language = player.locator('[data-table-language] select')
    with player.expect_navigation(wait_until='domcontentloaded'):
        language.select_option('pt-BR')
    player.wait_for_function('!!gravewrightMaps.board?.viewport()')
    player.set_viewport_size({'width': 390, 'height': 844})
    options = preferences(player)
    expect(options.get_by_text('Ponteiros do mouse', exact=True)).to_be_visible()
    expect(options.get_by_label('Mostrar ponteiros dos participantes', exact=True)).to_be_checked()
    expect(options.get_by_label('Compartilhar meu ponteiro', exact=True)).to_be_checked()
    options.scroll_into_view_if_needed()
    metrics = options.evaluate(MEASURE)
    assert not metrics['tiny'] and not metrics['overflow'], metrics
    player.screenshot(path=str(output / 'pointer-preferences-pt-BR-mobile.png'))
    print('Pointer preferences: independent visibility/sharing, reload persistence, account isolation, storage error and Portuguese mobile layout passed', flush=True)


if __name__ == '__main__':
    main(check, seed_extra=SEED, environment=environment)
