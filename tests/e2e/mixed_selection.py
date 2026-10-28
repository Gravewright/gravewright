"""Scene selection respects the active workspace for clicks and bulk operations."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    actor = gm.evaluate("()=>gravewrightRealtime.resourceCommand('actors','actor.create',{name:'Layer hero'})")
    gm.evaluate("p=>gravewrightRealtime.resourceCommand('tokens','place',p)", {'mapId':data['map'],'actorId':actor['id'],'gridX':3,'gridY':3})
    gm.evaluate("p=>gravewrightRealtime.mapCommand('objects',p)", {'mapId':data['map'],'area':'lights','action':'create','data':{'x':385,'y':245}})
    gm.evaluate("p=>gravewrightRealtime.mapCommand('objects',p)", {'mapId':data['map'],'area':'walls','action':'create','data':{'x1':350,'y1':350,'x2':490,'y2':350,'kind':'wall'}})
    token = gm.get_by_role('button', name='Token: Layer hero', exact=True)
    expect(token).to_be_visible()
    layers = gm.get_by_role('group', name='Layers', exact=True)
    layers.get_by_role('button', name='Game', exact=True).click()
    for x,y in [(385,245),(420,350)]:
        gm.mouse.move(x,y);gm.mouse.down();gm.mouse.move(x+70,y+70,steps=8);gm.mouse.up()
        gm.mouse.dblclick(x,y)
        gm.mouse.click(x,y,button='right')
        expect(gm.locator('.directory-context-menu')).to_have_count(0)
        expect(gm.locator('.light-editor')).to_have_count(0)
        expect(gm.locator('[data-selected-object]')).to_have_count(0)
    gm.mouse.move(330,220);gm.mouse.down();gm.mouse.move(510,380,steps=8);gm.mouse.up()
    expect(gm.locator('.selection-workspace [data-selected-object]')).to_have_count(0)
    gm.keyboard.press('Control+a')
    # The token may show its own outline, but authoring objects are never selected.
    assert gm.locator('.selection-workspace [data-selected-object]').count() == 0
    state = gm.evaluate("async p=>(await(await fetch('/api/maps/'+p.map+'/state')).json())",data)
    assert (state['lights'][0]['x'],state['lights'][0]['y']) == (385,245)
    assert state['walls'][0]['x1'] == 350

    layers.get_by_role('button', name='Lighting', exact=True).click()
    gm.mouse.move(385,245);gm.mouse.down();gm.mouse.move(455,315,steps=8);gm.mouse.up()
    gm.wait_for_function("async p=>{const s=await(await fetch('/api/maps/'+p.map+'/state')).json();return s.lights[0]?.x===455&&s.lights[0]?.y===315}",arg=data)
    gm.wait_for_function("document.querySelector('.selection-workspace [data-selected-object]')?.getAttribute('points')?.startsWith('446,306')")
    gm.wait_for_function("[...document.querySelectorAll('[aria-label=\"Light: none\"]')].some(e=>e.getAttribute('transform')?.startsWith('translate(455,315)'))")
    gm.mouse.dblclick(455,315)
    expect(gm.locator('.light-editor')).to_be_visible()
    gm.locator('.light-editor').get_by_role('button', name='Close', exact=True).click()
    gm.keyboard.press('Control+a')
    expect(gm.locator('.selection-workspace [data-selected-object]')).to_have_count(1)
    assert gm.locator('.selection-workspace [data-selected-object]').get_attribute('data-selected-object').startswith('light:')

    layers.get_by_role('button', name='Walls', exact=True).click()
    gm.keyboard.press('Control+a')
    expect(gm.locator('.selection-workspace [data-selected-object]')).to_have_count(1)
    assert gm.locator('.selection-workspace [data-selected-object]').get_attribute('data-selected-object').startswith('wall:')
    gm.mouse.move(420,350);gm.mouse.down();gm.mouse.move(490,420,steps=8);gm.mouse.up()
    gm.wait_for_function("async p=>{const s=await(await fetch('/api/maps/'+p.map+'/state')).json();return s.walls[0]?.x1===420&&s.walls[0]?.y1===420}",arg=data)
    layers.get_by_role('button', name='Game', exact=True).click()
    gm.keyboard.press('Delete')
    expect(gm.locator('[data-selected-object]')).to_have_count(0)
    state = gm.evaluate("async p=>(await(await fetch('/api/maps/'+p.map+'/state')).json())",data)
    assert len(state['walls']) == len(state['lights']) == 1
    expect(token).to_be_visible()
    gm.mouse.move(245,245);gm.mouse.down();gm.mouse.move(315,245,steps=8);gm.mouse.up()
    gm.wait_for_function("async p=>{const s=await(await fetch('/api/containers/'+p.campaign+'/maps/'+p.map+'/tokens')).json();return s.tokens[0]?.gridX===4}",arg=data)
    expect(gm.locator('.selection-workspace__error')).to_be_hidden()
    print('Game isolates authoring objects; Lighting and Walls allow their own edits; switching clears selection.',flush=True)


if __name__ == '__main__':
    main(check)
