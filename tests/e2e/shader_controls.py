"""Author shader controls in the native Blueprint editor and rehearse real shader deltas."""
import json
from playwright.sync_api import expect
from migration_closure import main
from builder_productivity import SEED as BASE_SEED
from map_pointer_preferences import environment
from map_builder import change_locale
from map_builder_reference import wait_ready

SEED=BASE_SEED+"""
from gravewright.maps.extra_objects import effect
from gravewright.maps.blueprints import default_blueprint
shader_id=str(uuid.uuid4())
shader=effect('shaders',{'name':'Synthetic glow','source':'void main() { finalColor = vec4(uColor, 1.0); }','x':5,'y':5,'radius':2,'color':'#ff0000'})
doc['shaders']=[{'id':shader_id,'layerId':layer,**shader}]
blueprint=default_blueprint('lever')
blueprint['graphs']['interact']={'nodes':[{'id':'event','type':'event','event':'interact','x':40,'y':60},
 {'id':'color','type':'shaderControl','targetId':shader_id,'property':'color','value':'#00ff00','x':350,'y':60}],
 'edges':[{'from':'event','to':'color','output':'next','kind':'execution'}]}
doc['decorations'][0]['blueprint']=blueprint
project.document=doc;project.save(update_fields=['document'])
result.update(shader=shader_id,object=doc['decorations'][0]['id'])
"""


def check(gm,player,data,output):
    base=gm.url.split('/game/')[0]
    gm.goto(base+'/game/'+data['campaign']+'/map-builder?project='+data['project']);wait_ready(gm)
    gm.locator('[data-builder-quick-tool=select]').click()
    target=gm.locator('[data-builder-decorations] [data-object-id="'+data['object']+'"]')
    target.dblclick()
    modal=gm.locator('[data-blueprint-editor]')
    if not modal.count():modal=gm.locator('.smart-object')
    expect(modal).to_be_visible()
    color=modal.locator('[data-blueprint-node=color]')
    expect(color.locator('[data-blueprint-param=targetId]')).to_have_value(data['shader'])
    expect(color.locator('[data-blueprint-param=property]')).to_have_value('color')
    color.locator('[data-blueprint-param=property]').select_option('opacity')
    color.locator('[data-blueprint-param=value]').fill('0.35')
    color.locator('[data-blueprint-param=value]').dispatch_event('change')
    modal.locator('[data-blueprint-add]').click()
    modal.locator('[data-blueprint-pick-type=shaderControl]').click()
    cards=modal.locator('[data-blueprint-node]')
    new=cards.evaluate_all("rows=>rows.map(row=>row.dataset.blueprintNode).find(id=>!['event','color'].includes(id)&&id.startsWith('node_'))")
    assert new
    node=modal.locator('[data-blueprint-node="'+new+'"]')
    node.locator('[data-blueprint-param=property]').select_option('speed')
    node.locator('[data-blueprint-param=value]').fill('2')
    node.locator('[data-blueprint-param=value]').dispatch_event('change')
    modal.locator('[data-blueprint-node=color] [data-blueprint-output=next]').click()
    modal.locator('[data-blueprint-input="'+new+'"]').click()
    gm.screenshot(path=str(output/'shader-control-editor.png'))
    modal.locator('[data-blueprint-close]').click()
    expect(modal).to_have_count(0)
    def saved():
        return gm.evaluate("""async d=>(await(await fetch('/api/containers/'+d.campaign+'/map-builder/projects/'+d.project)).json()).project""",data)
    gm.wait_for_function("""async d=>{const p=(await(await fetch('/api/containers/'+d.campaign+'/map-builder/projects/'+d.project)).json()).project;return p.document.decorations[0].blueprint.graphs.interact.nodes.some(n=>n.type==='shaderControl'&&n.property==='speed'&&n.value===2)}""",arg=data)
    project=saved()
    result=gm.evaluate("""async p=>{const {HttpClient}=await import('/static/gravewright_modules/http-client.js');return new HttpClient().post('/api/containers/'+p.campaign+'/map-builder/test',{request_id:crypto.randomUUID(),document:p.document,elementId:p.object,event:'interact'});} """,{**data,'document':project['document']})
    assert result['ok'],result
    shader=next(row for row in result['changes']['elements'] if row.get('sourceId')==data['shader'])
    assert shader['after']['data']['opacity']==.35 and shader['after']['data']['speed']==2
    assert saved()['document']['shaders'][0]['opacity']==1,'Rehearsal changed the draft'
    for locale in ('pt-BR','es'):
        change_locale(gm,locale,data['campaign']);gm.reload();wait_ready(gm)
        gm.locator('[data-builder-quick-tool=select]').click()
        gm.locator('[data-builder-decorations] [data-object-id="'+data['object']+'"]').dblclick()
        modal=gm.locator('.smart-object')
        expect(modal.locator('[data-blueprint-node=color] [data-blueprint-param=property]')).to_have_value('opacity')
        expect(modal.locator('[data-blueprint-node=color]').get_by_text('Controlar shader',exact=True)).to_be_visible()
        gm.screenshot(path=str(output/f'shader-control-{locale}.png'));modal.locator('[data-blueprint-close]').click()
    print('Shader controls: native editor, typed properties, connected execution, server rehearsal, unchanged source and locales passed')


if __name__=='__main__':
    main(check,seed_extra=SEED,environment=environment)
