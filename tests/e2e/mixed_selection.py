"""Mixed scene transforms use real pointer gestures and persisted state."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm,player,data,output):
    actor=gm.evaluate("()=>gravewrightRealtime.resourceCommand('actors','actor.create',{name:'Mixed hero'})")
    gm.evaluate("p=>gravewrightRealtime.resourceCommand('tokens','place',p)",{'mapId':data['map'],'actorId':actor['id'],'gridX':3,'gridY':3})
    gm.evaluate("p=>gravewrightRealtime.mapCommand('objects',p)",{'mapId':data['map'],'area':'lights','action':'create','data':{'x':385,'y':245}})
    token=gm.get_by_role('button',name='Token: Mixed hero',exact=True)
    expect(token).to_be_visible()
    token.click()
    gm.keyboard.down('Shift');gm.mouse.click(385,245);gm.keyboard.up('Shift')
    expect(gm.locator('[data-selected-object]')).to_have_count(2)
    gm.mouse.move(385,245);gm.mouse.down();gm.mouse.move(455,315,steps=8);gm.mouse.up()
    gm.wait_for_function("async p=>{const state=await(await fetch('/api/maps/'+p.map+'/state')).json();return state.lights[0]?.x===455 && state.lights[0]?.y===315}",arg=data)
    gm.wait_for_function("async p=>{const state=await(await fetch('/api/containers/'+p.campaign+'/maps/'+p.map+'/tokens')).json();return state.tokens[0]?.gridX===4 && state.tokens[0]?.gridY===4}",arg=data)
    expect(gm.locator('.selection-workspace__error')).to_be_hidden()
    gm.mouse.click(455,315,button='right')
    gm.get_by_role('button',name='Rotate selection +90°',exact=True).click()
    gm.wait_for_function("async p=>{const state=await(await fetch('/api/maps/'+p.map+'/state')).json();return state.lights[0]?.rotation===90}",arg=data)
    gm.keyboard.press('Escape')
    expect(gm.locator('[data-selected-object]')).to_have_count(0)
    light=gm.evaluate("async p=>(await(await fetch('/api/maps/'+p.map+'/state')).json()).lights[0]",data)
    gm.mouse.dblclick(light['x'],light['y'])
    expect(gm.locator('.light-editor')).to_be_visible()
    gm.locator('.light-editor header button').click()
    gm.get_by_role('group',name='Layers',exact=True).get_by_role('button',name='Game',exact=True).click()
    gm.keyboard.press('Control+a')
    expect(gm.locator('[data-selected-object]')).to_have_count(2)
    gm.keyboard.press('Delete')
    gm.get_by_role('button',name='Remove selection',exact=True).click()
    gm.wait_for_function("async p=>{const state=await(await fetch('/api/maps/'+p.map+'/state')).json();return state.lights.length===0}",arg=data)
    expect(token).to_have_count(0)
    print('Mixed token/light selection, translation, rotation and deletion passed',flush=True)

if __name__=='__main__':main(check)
