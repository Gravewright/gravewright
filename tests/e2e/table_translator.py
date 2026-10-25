"""Exercise new table and Builder controls with actual Translator catalogs.

Set GRAVEWRIGHT_TRANSLATOR_CATALOG_ROOT to a reviewed source catalog directory.
The fixture installs a disposable package; operator packages and data stay intact.
"""
from playwright.sync_api import expect

from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import upload_asset, wait_ready
import map_builder_blueprints as artwork
from migration_closure import main
from map_pointer_preferences import environment


SEED = """
from pathlib import Path
from zipfile import ZipFile
from gravewright.accounts.models import UserPreference
from gravewright.modules.packages import host
catalog_root=Path(os.environ.get('GRAVEWRIGHT_TRANSLATOR_CATALOG_ROOT',
    str(settings.BASE_DIR/'data/translator-source/gravewright_translator/catalogs')))
catalogs={locale:json.loads((catalog_root/(locale+'.json')).read_text(encoding='utf-8'))
          for locale in ('en','pt-BR','es')}
assert set(catalogs['en'])==set(catalogs['pt-BR'])==set(catalogs['es'])
manifest={'id':'gravewright.translator','version':'0.1.0','name':'Translator catalog fixture',
 'description':'Disposable integration fixture','author':'Gravewright tests','license':'MIT','entry':'main.js',
 'sdk':{'requires':'>=1.0.0 <2.0.0','tested':'1.0.0'},
 'locales':{locale:{'name':locale,'path':'locales/'+locale+'.json'} for locale in ('pt-BR','es')}}
archive_data=BytesIO()
with ZipFile(archive_data,'w') as archive:
 archive.writestr('manifest.json',json.dumps(manifest))
 archive.writestr('main.js','export default {start(){},stop(){}};')
 for locale in manifest['locales']:
  archive.writestr('locales/'+locale+'.json',json.dumps(catalogs[locale]))
host().install_local(archive_data.getvalue(),expected_type='module')
language_client=Client();language_client.force_login(owner)
activated=language_client.post('/api/module-packages/activation',{
 'id':manifest['id'],'version':manifest['version'],'enabled':True},content_type='application/json')
assert activated.status_code==200,activated.content
owner.name='Settings';owner.save(update_fields=['name'])
player.name='New';player.save(update_fields=['name'])
UserPreference.objects.create(user=owner,ping_color='#129abc')
UserPreference.objects.create(user=player,ping_color='#a1b2c3')
"""


def check(gm, player, data, output):
    base = gm.url.split('/game/')[0]
    def text(page, key, params=None):
        return page.evaluate('a=>gravewrightTranslator.t(a.key,a.params)', {'key': key, 'params': params or {}})

    def game(page):
        page.wait_for_function('!!gravewrightMaps.board?.viewport() && !!window.gravewrightTranslator')

    def mouse(page, x, y):
        position = page.evaluate('''a=>{
          const view=gravewrightMaps.board.viewport(),box=document.querySelector('.game-board__surface').getBoundingClientRect();
          return [box.x+view.x+a.x*view.scale,box.y+view.y+a.y*view.scale];
        }''', {'x': x, 'y': y})
        page.mouse.move(*position)

    gm_id = gm.locator('#table-workspace').get_attribute('data-profile-id')
    for locale in ('en', 'pt-BR', 'es'):
        for page in (gm, player):
            change_locale(page, locale, data['campaign'])
            page.reload()
            game(page)
            assert page.locator('html').get_attribute('lang') == locale
        gm.locator('.game-menubar__logo').click()
        gm.locator('.house-menu__section').nth(2).click()
        options = gm.locator('[data-table-pointers]')
        expect(options.get_by_label(text(gm, "Show participants' pointers"), exact=True)).to_be_checked()
        expect(options.get_by_label(text(gm, 'Share my pointer'), exact=True)).to_be_checked()
        if locale != 'en':
            assert text(gm, 'Mouse pointers') != 'Mouse pointers'
        gm.locator('.house-menu__section').nth(3).click()
        shortcuts = gm.locator('[data-shortcut-settings]')
        expect(shortcuts.locator('header strong')).to_have_text(text(gm, 'Keyboard shortcuts'))
        expect(shortcuts.locator('[data-shortcut-action="tool:game:draw"] label')).to_have_text(text(gm, 'Draw'))
        expect(shortcuts.locator('[data-shortcut-reset]')).to_have_text(text(gm, 'Restore defaults'))
        gm.screenshot(path=str(output / f'translator-preferences-{locale}.png'))
        gm.locator('.house-menu__close').click()

        gm.locator('[data-shortcut-layer=game] [data-dock-tool=measure]').click()
        panel = gm.locator('.measure-panel')
        panel.get_by_label(text(gm, 'Title'), exact=True).check()
        mouse(gm, 200, 200)
        gm.mouse.down()
        mouse(gm, 400, 350)
        gm.mouse.up()
        title = gm.get_by_role('textbox', name=text(gm, 'Measurement title'), exact=True)
        expect(title).to_be_visible()
        title.fill('Settings')
        expect(gm.locator('.measurement-workspace__handle').first).to_have_attribute(
            'aria-label', text(gm, 'Move {0}', {'0': text(gm, 'Line')}))
        expect(panel.locator('header small')).to_contain_text(text(gm, ' / cell').strip())
        panel.locator('header button').click()
        expect(gm.locator('.measurement-title__text').first).to_have_text('Settings')
        expect(gm.locator('.measurement-title__text').first).to_have_attribute('title', 'Settings')

        gm.evaluate('gravewrightMaps.createScene()')
        choice = gm.locator('[data-map-create=empty]')
        expect(choice.locator('strong')).to_have_text(text(gm, 'Empty map'))
        choice.click()
        dialog = gm.locator('.game-scene-empty')
        expect(dialog.locator('header strong')).to_have_text(text(gm, 'Empty map'))
        dialog.locator('[name=name]').fill('New')
        dialog.get_by_label(text(gm, 'Background color'), exact=True).fill('#354b66')
        dialog.get_by_label(text(gm, 'Width (px)'), exact=True).fill('700')
        dialog.get_by_label(text(gm, 'Height (px)'), exact=True).fill('700')
        expect(dialog.get_by_label(text(gm, 'Activate after creation'), exact=True)).to_be_checked()
        with gm.expect_response(lambda response: response.url.endswith('/scene-empty')) as created:
            dialog.locator('[type=submit]').click()
        assert created.value.ok, created.value.text()
        scene = created.value.json()['id']
        for page in (gm, player):
            page.wait_for_function('id=>gravewrightMaps.current?.id===id && !!gravewrightMaps.board?.viewport()', arg=scene)
        gm.evaluate('gravewrightMaps.showDirectory()')
        row = gm.locator(f'#maps-panel [data-scene-id="{scene}"]')
        expect(row.locator('strong')).to_have_text('New')
        expect(row.locator('.game-scene-gm')).to_have_attribute('title', text(gm, 'Your current scene'))
        row.click(button='right')
        gm.get_by_role('menuitem', name=text(gm, 'Activate for selected players'), exact=True).click()
        activation = gm.get_by_role('dialog', name=text(gm, 'Activate for selected players'), exact=True)
        expect(activation.locator('[data-activation-scene]')).to_have_text('New')
        expect(activation.get_by_role('checkbox', name='New', exact=True)).to_be_visible()
        gm.screenshot(path=str(output / f'translator-scene-audience-{locale}.png'))
        activation.locator('.directory-dialog__close').click()
        gm.evaluate('gravewrightMaps.toggle()')
        mouse(gm, 200, 200)
        mouse(player, 300, 300)
        expect(gm.locator(f'[data-map-pointer="{data["player_id"]}"] .map-pointer__name')).to_have_text('New')
        expect(player.locator(f'[data-map-pointer="{gm_id}"] .map-pointer__name')).to_have_text('Settings')

    # Author uploaded Smart Objects in both supported translated interfaces.
    review = BuilderReview(gm, data['campaign'])
    review.builder = base + review.builder
    review.api = base + review.api
    for locale in ('pt-BR', 'es'):
        change_locale(gm, locale, data['campaign'])
        gm.goto(review.builder)
        wait_ready(gm)
        asset = upload_asset(gm, 'decoration', f'Synthetic {locale} chest.png', artwork.artwork('#ad642b'))['id']
        builder_tool(gm, 'decoration')
        gm.locator('[data-builder-brush-material]').select_option(asset)
        review.stroke((8, 8), (10, 10))
        saved = review.save()
        identifier = next(item['id'] for item in saved['document']['decorations'] if item['assetId'] == asset)
        builder_tool(gm, 'select')
        builder_workspace(gm)
        gm.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').first.click(button='right')
        gm.locator('[data-builder-object-action=behavior]').click()
        properties = gm.locator('[data-builder-property-modal=behavior]')
        area = properties.get_by_label(text(gm, 'Circular activation area'), exact=True)
        expect(area).to_be_visible()
        area.check()
        expect(properties.get_by_label(text(gm, 'Activation radius (cells)'), exact=True)).to_have_value('1.5')
        expect(properties.get_by_text(text(gm, 'Drag the circle handle to resize the area. Connect On area enter or On area exit in the Smart Object to run effects without clicking.'), exact=True)).to_be_visible()
        gm.screenshot(path=str(output / f'translator-circular-area-{locale}.png'))
        properties.locator('[data-builder-edit-behavior]').click()
        expect(gm.locator('[data-smart-object-modal]')).to_be_visible()
        gm.locator('[data-blueprint-close]').click()

    # Deactivating the language pack restores the English host fallback while
    # preserving the authored scene and the account's explicit locale choice.
    gm.evaluate('''async()=>{
      const {HttpClient}=await import('/static/gravewright_modules/http-client.js');
      return new HttpClient().post('/api/module-packages/activation',
        {id:'gravewright.translator',version:'0.1.0',enabled:false});
    }''')
    gm.goto(f'{base}/game/{data["campaign"]}')
    gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    assert gm.locator('html').get_attribute('lang') == 'en'
    gm.locator('.game-menubar__logo').click()
    gm.locator('.house-menu__section').nth(3).click()
    expect(gm.locator('[data-shortcut-settings] header strong')).to_have_text('Keyboard shortcuts')
    gm.evaluate('''async()=>{
      const {HttpClient}=await import('/static/gravewright_modules/http-client.js');
      return new HttpClient().post('/api/module-packages/activation',
        {id:'gravewright.translator',version:'0.1.0',enabled:true});
    }''')
    gm.reload()
    game(gm)
    assert gm.locator('html').get_attribute('lang') == 'es'
    print('Translator: real catalogs en/pt-BR/es, shortcuts, pointer preferences, measurement titles, authored names, empty maps, scene audiences, uploaded Smart Objects, circular areas and English fallback passed', flush=True)


if __name__ == '__main__':
    main(check, seed_extra=SEED, environment=environment)
