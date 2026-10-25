"""Six Builder workflows on real controls with disposable artwork and campaign state."""
from playwright.sync_api import expect
from migration_closure import main
from map_builder_reference import wait_ready
from table_translator import SEED as LANGUAGE_SEED
from map_pointer_preferences import environment
from map_builder import change_locale

SEED = LANGUAGE_SEED + """
import uuid
from gravewright.maps.models import MapAsset,MapBuilderProject
from gravewright.actors.models import Actor
from gravewright.pdf_system.schema import normalize
buf=BytesIO();Image.new('RGBA',(32,32),'#65a075').save(buf,'PNG')
asset=MapAsset(campaign=c,name='Synthetic tree',width=32,height=32)
asset.file.save('tree.png',ContentFile(buf.getvalue()),save=True)
layer=str(uuid.uuid4())
doc={'schemaVersion':3,'name':'Productivity fixture','columns':20,'rows':15,'cellSize':40,'background':'#253038',
 'layers':[{'id':layer,'name':'Environment','visible':True,'locked':False}],
 'floors':[],'walls':[],'doors':[],'decorations':[],'lights':[],'particles':[],'shaders':[],'regions':[],
 'assets':[{'assetId':str(asset.pk),'role':'decoration'}]}
for i,(x,y) in enumerate(((2,2),(5,4),(9,6))):
 doc['decorations'].append({'id':str(uuid.uuid4()),'name':'Tree '+str(i),'assetId':str(asset.pk),'layerId':layer,'x':x,'y':y,'width':1,'height':1,'rotation':0,'lever':{'state':'off'},'presenceRadius':1.5})
doc['walls']=[{'id':str(uuid.uuid4()),'layerId':layer,'x1':12,'y1':0,'x2':12,'y2':15,'assetId':None,'thickness':.2}]
project=MapBuilderProject.objects.create(campaign=c,name=doc['name'],document=doc)
Actor.objects.create(campaign=c,name='Test walker',data=normalize({}))
result.update(project=str(project.pk),asset=str(asset.pk))
"""


def check(gm,player,data,output):
    base=gm.url.split('/game/')[0]
    errors=[];gm.on('pageerror',lambda error:(errors.append(str(error)),print('Builder page error:',str(error),flush=True)))
    gm.goto(base+'/game/'+data['campaign']+'/map-builder?project='+data['project'])
    try:
        wait_ready(gm)
    except Exception:
        gm.screenshot(path=str(output/'builder-productivity-failure.png'))
        print('Builder startup errors:',errors,flush=True)
        raise
    def point(x,y):
        return gm.evaluate("""p=>{const s=document.querySelector('[data-builder-canvas]'),q=new DOMPoint(p.x,p.y).matrixTransform(s.getScreenCTM());return [q.x,q.y]}""",{'x':x,'y':y})
    def tools():
        gm.locator('[data-builder-productivity-open]').click()
        modal=gm.locator('[data-builder-productivity]');expect(modal).to_be_visible();return modal
    gm.locator('[data-builder-quick-tool=select]').click()
    for index,(x,y) in enumerate(((2.5,2.5),(5.5,4.5),(9.5,6.5))):
        if index:gm.keyboard.down('Shift')
        gm.mouse.click(*point(x,y))
        if index:gm.keyboard.up('Shift')
    modal=tools()
    modal.locator('[data-builder-arrange=top]').click()
    modal.locator('[data-builder-group-name]').fill('Garden')
    modal.locator('[data-builder-group-selection]').click()
    modal.locator('[data-builder-show-areas]').check()
    modal.locator('[data-builder-preset-name]').fill('Reusable garden')
    modal.locator('[data-builder-save-preset]').click()
    expect(modal.locator('[data-builder-place-preset]')).to_have_count(1)
    assert not modal.locator('[role=alert]').inner_text()
    gm.screenshot(path=str(output/'builder-productivity-tools.png'))
    modal.locator('[data-builder-place-preset]').click()
    expect(modal).to_have_count(0)
    gm.mouse.click(*point(2,9))
    expect(gm.locator('[data-builder-decorations] [data-object-id]')).to_have_count(6)
    expect(gm.locator('[data-builder-area-overview]')).to_have_count(6)
    gm.locator('[data-builder-undo]').click()
    expect(gm.locator('[data-builder-decorations] [data-object-id]')).to_have_count(3)
    # Pick the imported image, then configure the dedicated object brush.
    modal=tools();modal.locator('[data-builder-object-brush]').check()
    modal.locator('[data-builder-scatter-option=spacing]').fill('1')
    modal.locator('[data-builder-scatter-option=spacing]').dispatch_event('change')
    modal.get_by_role('button',name='Close',exact=True).click()
    # Select through the normal Objects library rather than changing saved project data.
    gm.locator('[data-builder-role=decoration]').click()
    gm.locator('[data-asset-id="'+data['asset']+'"]').click()
    a,b=point(3,11),point(8,11)
    gm.mouse.move(*a);gm.mouse.down();gm.mouse.move(*b,steps=12);gm.mouse.up()
    count=gm.locator('[data-builder-decorations] [data-object-id]').count()
    assert count>=8,count
    gm.locator('[data-builder-undo]').click()
    expect(gm.locator('[data-builder-decorations] [data-object-id]')).to_have_count(3)
    modal=tools();modal.locator('[data-builder-player-test]').click()
    simulation=gm.locator('[data-builder-player-simulation]');expect(simulation).to_be_visible()
    expect(simulation.locator('[data-builder-test-pawn]')).to_have_count(1)
    game=simulation.locator('[data-builder-player-test-map]')
    game.focus();gm.keyboard.press('ArrowRight')
    expect(simulation.locator('[data-builder-test-pawn]')).to_have_attribute('cx','2.5')
    with gm.expect_response(lambda response:response.url.endswith('/map-builder/test') and response.request.method=='POST') as response:
        simulation.get_by_role('button',name='Interact',exact=True).click()
    assert response.value.status==200,response.value.text()
    expect(simulation.locator('[data-builder-player-test-log] li')).not_to_have_count(0)
    gm.screenshot(path=str(output/'builder-player-simulation.png'))
    gm.keyboard.press('Escape')
    expect(simulation).to_have_count(0)
    gm.wait_for_timeout(700)
    assert not errors,errors
    for width in (1440,390):
        gm.set_viewport_size({'width':width,'height':900});modal=tools()
        gm.screenshot(path=str(output/f'builder-tools-{width}.png'))
        box=modal.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width
        gm.keyboard.press('Escape')
    for locale,title,library in (('pt-BR','Ferramentas do Builder','Meus objetos'),('es','Herramientas de Builder','Mis objetos')):
        change_locale(gm,locale,data['campaign']);gm.reload();wait_ready(gm)
        modal=tools();expect(modal).to_have_attribute('aria-label',title)
        expect(modal.get_by_role('heading',name=library,exact=True)).to_be_visible()
        gm.screenshot(path=str(output/f'builder-tools-{locale}.png'));gm.keyboard.press('Escape')
    print('Builder productivity: grouping, alignment, areas, preset save/place, brush undo and player rehearsal passed')


if __name__=='__main__':
    main(check,seed_extra=SEED,environment=environment)
