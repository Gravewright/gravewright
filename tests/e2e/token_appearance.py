"""Native token appearance editor, filtered GM/player state and turn indicators."""
from playwright.sync_api import expect

from migration_closure import main
from map_pointer_preferences import environment
from table_translator import SEED as LANGUAGE_SEED
from map_builder import change_locale


SEED = LANGUAGE_SEED + """
from gravewright.actors.models import Actor
from gravewright.tokens.models import Token
from gravewright.pdf_system.schema import normalize
actor=Actor.objects.create(campaign=c,name='Guardian',permissions={str(player.pk):'owner'},
 data=normalize({'bars':{'bar_1':{'value':7,'max':10},'bar_2':{'value':3,'max':5}}}))
token=Token.objects.create(scene=s,actor=actor,grid_x=3,grid_y=3)
result['token']=str(token.pk)
"""


def check(gm, player, data, output):
    def row(page):
        return page.evaluate("""async p => (await (await fetch('/api/containers/'+p.campaign+'/maps/'+p.map+'/tokens')).json()).tokens.find(t=>t.id===p.token)""", data)

    hero = gm.get_by_role('button', name='Token: Guardian', exact=True)
    hero.click(button='right')
    gm.get_by_role('menuitem', name='Configure', exact=True).click()
    editor = gm.locator('.token-editor')
    expect(editor).to_be_visible()
    editor.locator('[name=nameDisplay]').select_option('always')
    editor.locator('[name=bar_1Visibility]').select_option('owner')
    editor.locator('[name=bar_2Visibility]').select_option('gm')
    editor.locator('[name=bar_1Color]').fill('#aabbcc')
    editor.locator('[name=bar_2Color]').fill('#cc4455')
    gm.screenshot(path=str(output / 'token-appearance-editor.png'))
    editor.get_by_role('button', name='Save', exact=True).click()
    expect(editor).to_have_count(0)
    gm.wait_for_function("p=>window.gravewrightTokenState.tokens.some(t=>t.id===p.token && t.nameDisplay==='always')", arg=data)
    player.wait_for_function("p=>window.gravewrightTokenState.tokens.some(t=>t.id===p.token && t.nameDisplay==='always')", arg=data)
    assert set(row(player)['bars']) == {'bar_1'}
    assert row(player)['bars']['bar_1']['color'] == '#aabbcc'
    assert row(gm)['bars']['bar_2']['color'] == '#cc4455'
    # Use the real workspace combat event: the indicator is independent of system rules.
    def turn():
        gm.evaluate("""p=>{
            window.gravewrightCombatState={active:true,sceneId:p.map,combatants:[{token_id:p.token,is_current:true}]};
            window.dispatchEvent(new CustomEvent('gravewright:combat-state'));
        }""", data)
    turn()
    expect(gm.locator('[data-combat-current]')).to_have_count(1)
    gm.screenshot(path=str(output / 'token-turn-indicator.png'))
    hero.click(button='right')
    gm.get_by_role('menuitem', name='Configure', exact=True).click()
    expect(editor.locator('[name=nameDisplay]')).to_have_value('always')
    editor.locator('[name=showTurnIndicator]').uncheck()
    editor.get_by_role('button', name='Save', exact=True).click()
    expect(editor).to_have_count(0)
    expect(gm.locator('[data-combat-current]')).to_have_count(0)
    for width in (1440, 390):
        gm.set_viewport_size({'width':width,'height':900})
        hero.click(button='right')
        gm.get_by_role('menuitem', name='Configure', exact=True).click()
        expect(editor).to_be_visible()
        box=editor.bounding_box()
        assert box['x'] >= 0 and box['x']+box['width'] <= width
        editor.locator('[name=bar_2Color]').scroll_into_view_if_needed()
        gm.screenshot(path=str(output / f'token-editor-{width}.png'))
        gm.keyboard.press('Escape')
    gm.set_viewport_size({'width':1440,'height':900})
    for locale, label in (('pt-BR', 'Exibição do nome do token'), ('es', 'Visualización del nombre del token')):
        change_locale(gm, locale, data['campaign'])
        gm.reload()
        gm.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
        gm.locator('.token-workspace rect[role=button]').first.click(button='right')
        configure = gm.evaluate("gravewrightTranslator.t('Configure')")
        gm.get_by_role('menuitem', name=configure, exact=True).click()
        expect(editor.get_by_role('combobox', name=label, exact=True)).to_have_value('always')
        gm.screenshot(path=str(output / f'token-editor-{locale}.png'))
        gm.keyboard.press('Escape')
    print('Token appearance: native save, owner/GM filtering, colors, turn toggle and responsive editor passed')


if __name__ == '__main__':
    main(check, seed_extra=SEED, environment=environment)
