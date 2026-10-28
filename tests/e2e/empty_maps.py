"""Create native solid-color maps from the scene modal without image uploads."""

from io import BytesIO

from migration_closure import main
from PIL import Image
from playwright.sync_api import expect


LANGUAGE_SEED = """
from gravewright.maps.models import Folder
result['folder'] = str(Folder.objects.create(campaign=c, label='Empty map encounters').pk)
from gravewright.modules.models import Package
Package.objects.create(module_id='gravewright.translator', version='1.0.0',
    digest='a' * 64, record={}, global_enabled=True,
    manifest={'id':'gravewright.translator','name':'Synthetic languages','version':'1.0.0',
              'sdk':{'requires':'>=0.0.0'}},
    locale_catalogs={locale:{'name':locale,'messages':{'Settings':'Settings'}}
                     for locale in ('pt-BR','es')})
"""


def check(gm, player, data, output):
    def create(color, grid, width, height, name, activate=True):
        player_map = player.evaluate('gravewrightMaps.current?.id')
        gm.evaluate('gravewrightMaps.createScene()')
        choice = gm.get_by_role('dialog', name='New scene', exact=True)
        expect(choice.locator('[data-map-create="upload"]')).to_be_visible()
        expect(choice.locator('[data-map-create="builder"]')).to_be_visible()
        expect(choice.locator('[data-map-create="uvtt"]')).to_be_visible()
        choice.locator('[data-map-create="empty"]').click()
        form = gm.get_by_role('dialog', name='Empty map', exact=True)
        expect(form.locator('input[type=file]')).to_have_count(0)
        options = {'gridSize': '96', 'imageScale': '1.5', 'measureValue': '2.5', 'measureUnit': 'm', 'gridColor': '#aabbcc'}
        for key, value in options.items():
            form.locator(f'[name={key}]').fill(value)
        form.locator('[name=gridOpacity]').fill('0.7')
        form.locator('[name=groupId]').select_option(data['folder'])
        form.locator('[name=visibility]').select_option('players' if activate else 'gm')
        assert form.evaluate('e=>e.scrollWidth<=e.clientWidth')
        form.get_by_label('Scene name', exact=True).fill(name)
        form.get_by_label('Background color', exact=True).fill(color)
        form.get_by_label('Width (px)', exact=True).fill(str(width))
        form.get_by_label('Height (px)', exact=True).fill(str(height))
        form.get_by_label('Show grid', exact=True).set_checked(grid)
        form.get_by_label('Activate after creation', exact=True).set_checked(activate)
        gm.screenshot(path=str(output / f'empty-map-form-{grid}.png'))
        with gm.expect_response(lambda r: r.url.endswith('/scene-empty') and r.request.method == 'POST') as response:
            form.get_by_role('button', name='Create map', exact=True).click()
        assert response.value.status == 201
        scene = response.value.json()
        assert scene['name'] == name
        assert scene['gridSize'] == 96 and scene['imageScale'] == 1.5
        assert scene['measureValue'] == 2.5 and scene['measureUnit'] == 'm'
        assert scene['gridColor'] == '#aabbcc' and scene['gridOpacity'] == 0.7
        assert scene['groupId'] == data['folder']
        assert scene['visibility'] == ('players' if activate else 'gm')
        assert (scene['width'], scene['height'], scene['gridVisible']) == (width, height, grid)
        expect(form).to_have_count(0)
        for page in ((gm, player) if activate else (gm,)):
            page.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=scene['id'])
        if not activate:
            player.reload()
            player.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=player_map)
        return scene

    scene = create('#123456', False, 1400, 1050, 'Dangerous crossing')
    gm.wait_for_function('id => streamEvents.some(e => e.kind === "scene.viewport.ready" && e.region?.mapId === id)', arg=scene['id'])
    canvas = gm.locator('.game-board__surface canvas').first
    # Verify the actual rendered scene color, rather than just the form response.
    def rendered_color():
        with Image.open(BytesIO(canvas.screenshot())) as image:
            return image.convert('RGB').getpixel((image.width // 2, image.height // 2))

    for _ in range(30):
        pixel = rendered_color()
        if pixel == (18, 52, 86):
            break
    assert pixel == (18, 52, 86), pixel
    gm.screenshot(path=str(output / 'empty-map-no-grid.png'))
    gm.reload()
    gm.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=scene['id'])
    assert gm.evaluate('gravewrightMaps.current.gridVisible') is False
    assert gm.evaluate('gravewrightMaps.current.name') == 'Dangerous crossing'
    assert gm.evaluate('gravewrightMaps.current.gridSize') == 96
    assert gm.evaluate('gravewrightMaps.current.measureUnit') == 'm'
    gm.evaluate("p=>gravewrightRealtime.mapCommand('objects',p)",{'mapId':scene['id'],'area':'walls','action':'create','data':{'kind':'wall','x1':100,'y1':100,'x2':200,'y2':100}})
    gm.evaluate("p=>gravewrightRealtime.mapCommand('objects',p)",{'mapId':scene['id'],'area':'lights','action':'create','data':{'x':300,'y':300}})
    state=gm.evaluate("async id=>(await fetch('/api/maps/'+id+'/state')).json()",scene['id'])
    assert len(state['walls'])==1 and len(state['lights'])==1
    gm.set_viewport_size({'width': 390, 'height': 844})
    prepared = create('#63794a', True, 700, 700, 'Prepared encounter', activate=False)
    gm.reload()
    gm.wait_for_function('id => gravewrightMaps.current?.id === id && !!gravewrightMaps.board?.viewport()', arg=prepared['id'])
    gm.screenshot(path=str(output / 'empty-map-grid-mobile.png'))
    for locale, title in (('pt-BR', 'Mapa Vazio'), ('es', 'Mapa vacío')):
        gm.locator('.game-menubar__logo').click()
        gm.locator('.house-menu__section').nth(2).click()
        with gm.expect_navigation(wait_until='domcontentloaded'):
            gm.locator('[data-table-language] select').select_option(locale)
        gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
        gm.evaluate('gravewrightMaps.createScene()')
        gm.locator('[data-map-create="empty"]:visible').click()
        form = gm.get_by_role('dialog', name=title, exact=True)
        expect(form).to_be_visible()
        gm.screenshot(path=str(output / f'empty-map-form-{locale}.png'))
        form.locator('.directory-dialog__close').click()
    print('Empty map: custom names, shared creation settings, folder, private visibility, walls, lights, optional activation, grid toggle, rendered color, reload and player broadcast preservation passed', flush=True)


if __name__ == '__main__':
    main(check, seed_extra=LANGUAGE_SEED)
