"""Measure actual area/interaction-to-GPU artwork updates on two live boards.

All state is synthetic and installation-local. Browser probes observe frames,
transport and image decoding without screenshot polling in the timed interval.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import os
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


PROBE = r"""(() => {
  const probe=window.__eventLatency={events:[],fetches:[],decodes:[],uploads:[],pixel:null,watch:null,lastActivity:performance.now()};
  const mark=(kind,data={})=>probe.events.push({kind,at:performance.now(),...data});
  for(const type of ['pointerup','dblclick','keydown']) addEventListener(type,event=>{
    if(probe.watch)mark(type,{key:event.key});
  },true);
  addEventListener('gravewright:api-event',event=>{
    probe.lastActivity=performance.now();
    if(probe.watch)mark(event.detail.type,{payload:event.detail.payload});
  });
  const send=WebSocket.prototype.send;
  WebSocket.prototype.send=function(value){
    if(probe.watch){try{const valueJSON=JSON.parse(value);mark('send:'+valueJSON.type,{payload:valueJSON.payload});}catch{}}
    return send.call(this,value);
  };
  const fetchOriginal=window.fetch;
  window.fetch=function(input,...args){
    const url=String(input?.url||input),at=performance.now();
    if(probe.watch)probe.fetches.push({url,at});
    return fetchOriginal.call(this,input,...args);
  };
  const decode=window.createImageBitmap;
  window.createImageBitmap=async function(...args){
    const at=performance.now(),value=await decode.apply(this,args);
    if(probe.watch)probe.decodes.push({at,done:performance.now(),width:value.width,height:value.height});
    return value;
  };
  const contexts=new Set(),context=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(kind,...args){
    const result=context.call(this,kind,...args);
    if(result&&/webgl/.test(kind))contexts.add(result);
    return result;
  };
  for(const ctor of [window.WebGLRenderingContext,window.WebGL2RenderingContext].filter(Boolean)){
    const upload=ctor.prototype.texImage2D;
    ctor.prototype.texImage2D=function(...args){
      if(probe.watch)probe.uploads.push(performance.now());
      return upload.apply(this,args);
    };
  }
  function sample(){
    const watch=probe.watch;
    if(!watch||probe.pixel||!window.gravewrightMaps?.board)return;
    const view=gravewrightMaps.board.viewport(),surface=document.querySelector('.game-board__surface');
    if(!view||!surface)return;
    const surfaceRect=surface.getBoundingClientRect();
    for(const gl of contexts){
      const canvas=gl.canvas;
      if(!canvas.isConnected||!canvas.closest('.game-board'))continue;
      if(gl.getParameter(gl.FRAMEBUFFER_BINDING)!==null)continue;
      const rect=canvas.getBoundingClientRect();
      const x=Math.round((surfaceRect.x+view.x+watch.x*view.scale-rect.x)*canvas.width/rect.width);
      const y=canvas.height-1-Math.round((surfaceRect.y+view.y+watch.y*view.scale-rect.y)*canvas.height/rect.height);
      if(x<0||y<0||x>=canvas.width||y>=canvas.height)continue;
      const color=new Uint8Array(4);gl.readPixels(x,y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,color);
      const matches=watch.color==='orange'?color[0]>color[2]+70:color[2]>color[0]+70;
      if(matches){probe.pixel={at:performance.now(),rgb:[...color],x,y};mark('gpu-pixel',probe.pixel);}
    }
  }
  const raf=window.requestAnimationFrame;
  window.requestAnimationFrame=function(callback){return raf.call(window,time=>{callback(time);sample();});};
  probe.start=watch=>{probe.events=[];probe.fetches=[];probe.decodes=[];probe.uploads=[];probe.pixel=null;
    probe.watch=watch;mark('armed');};
  probe.finish=()=>{probe.watch=null;};
})();"""


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign=seed['campaign']
    cases, errors, measurements, clients, contexts = [], [], [], {}, []
    scene=None
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(**({'executable_path':str(executable)} if executable else {}))

        def client(role):
            context=browser.new_context(base_url=base,viewport={'width':1440,'height':900})
            context.add_cookies([{**seed['sessions'][role],'url':base}])
            context.add_init_script(PROBE)
            page=context.new_page()
            page.on('pageerror',lambda error:errors.append({'role':role,'error':str(error)}))
            contexts.append(context);clients[role]=page
            return page

        gm=client('gm');review=BuilderReview(gm,campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence','seated')

        def state(page=gm):
            response=page.request.get(f'/api/maps/{scene}/state')
            assert response.ok,response.text()
            return response.json()

        def point(page,x,y):
            return page.evaluate('''p=>{const r=document.querySelector('.game-board__surface').getBoundingClientRect(),
              v=gravewrightMaps.board.viewport();return {x:r.x+v.x+p.x*v.scale,y:r.y+v.y+p.y*v.scale};}''',{'x':x,'y':y})

        def screenshot_pixel(page,row):
            at=point(page,row['x'],row['y'])
            with Image.open(BytesIO(page.screenshot())) as shot:
                return shot.convert('RGB').getpixel((round(at['x']),round(at['y'])))

        def diagnostics():
            (output/'measurements.json').write_text(json.dumps({'cases':cases,'measurements':measurements,
                'pageErrors':errors,'probes':{role:page.evaluate('''()=>({events:__eventLatency.events,
                  fetches:__eventLatency.fetches,decodes:__eventLatency.decodes,uploads:__eventLatency.uploads,
                  pixel:__eventLatency.pixel})''') for role,page in clients.items()}},indent=2),encoding='utf-8')

        try:
            gm.goto(review.builder);wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic event latency')
            gm.locator('[data-builder-quick-name]').press('Tab')
            assets=[]
            for index,color in enumerate(['#245dc9','#ed7822','#375849','#817544','#595277','#376c81','#6d554b','#657735']):
                assets.append(upload_asset(gm,'decoration',f'Synthetic latency {index}.png',harness.artwork(color))['id'])
            blue,orange=assets[:2]
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state','saved',timeout=20_000)
            project=review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document=deepcopy(project['document']);layer=document['layers'][0]['id']
            empty,target,direct,private=(str(uuid4()) for _ in range(4))
            graphs={event:chain(event,[node('sprite','sprite',appearance='asset',assetId=asset)],
                [node('target','reference',targetId=target)],[('target','door','sprite','target')])
                for event,asset in (('presence:enter',orange),('presence:exit',blue))}
            direct_graph=chain('interact',[node('sprite','sprite',appearance='asset',assetId=orange)],
                [node('target','reference',targetId=target)],[('target','door','sprite','target')])
            document['decorations']=[
                {'id':empty,'layerId':layer,'assetId':None,'empty':True,'name':'Synthetic latency area',
                 'x':8,'y':8,'width':4,'height':3,'rotation':0,'lever':{'state':'off'},
                 'blueprint':behavior('lever',graphs)},
                {'id':target,'layerId':layer,'assetId':blue,
                 'x':16,'y':8,'width':2,'height':2,'rotation':0},
                {'id':direct,'layerId':layer,'assetId':blue,
                 'x':22,'y':8,'width':2,'height':2,'rotation':0,'lever':{'state':'off'},
                 'blueprint':behavior('lever',{'interact':direct_graph})},
                {'id':private,'layerId':layer,'assetId':orange,
                 'x':25,'y':8,'width':2,'height':2,'rotation':0},
            ]
            for index in range(48):
                document['decorations'].append({'id':str(uuid4()),'layerId':layer,'assetId':assets[2+index%6],
                    'x':2+index%12*3,'y':15+index//12*3,'width':1.5,'height':1.5,'rotation':0})
            project=review.store(project['id'],project['version'],project['folderId'],document)
            gm.goto(review.builder+'?project='+project['id']);wait_ready(gm);close_panel(gm)
            with gm.expect_response(lambda response:response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok,generated.value.text()
            game(gm);project=review.project(project['id']);scene=project['sceneId']
            native=state();owner=next(row for row in native['images'] if row.get('empty'))
            target_row=next(row for row in native['images'] if row.get('asset_id')==blue and not row.get('lever'))
            direct_row=next(row for row in native['images'] if row.get('lever') and not row.get('empty'))
            private_row=next(row for row in native['images'] if row.get('asset_id')==orange)
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('update',{mapId:a.scene,version:a.version,
              settings:{visibility:'players'}})''',{'scene':scene,'version':project['sceneVersion']})
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})",scene)
            gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{mapId:scene,
              area:'lighting',action:'update',data:{mode:'none',darkness:0,lights_out:false}})''',scene)
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,
              area:'images',action:'update',data:{id:a.id,layer:'gm-image-layer'}})''',{'scene':scene,'id':private_row['id']})
            actor=gm.evaluate("()=>gravewrightRealtime.resourceCommand('actors','actor.create',{name:'Synthetic latency traveler'})")
            gm.evaluate("id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',{id,permissions:{default:'owner'}})",actor['id'])
            gm.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',{mapId:a.scene,
              actorId:a.actor,gridX:5,gridY:9})''',{'scene':scene,'actor':actor['id']})
            gm.locator('.game-menubar__layer').get_by_text('Game',exact=True).click()
            player=client('player');player.goto(f'/game/{campaign}');game(player)
            player.wait_for_function('id=>gravewrightMaps.current.id===id',arg=scene)
            for page in clients.values():page.wait_for_timeout(300)

            def arm(color):
                for page in clients.values():page.evaluate('watch=>__eventLatency.start(watch)',
                    {'x':target_row['x'],'y':target_row['y'],'color':color})

            def collect(label,origin):
                for page in clients.values():
                    page.wait_for_function('__eventLatency.pixel!==null',timeout=20_000)
                record={'case':label,'origin':origin,'clients':{}}
                for role,page in clients.items():
                    value=page.evaluate('''()=>{__eventLatency.finish();return {timeOrigin:performance.timeOrigin,events:__eventLatency.events,
                      fetches:__eventLatency.fetches,decodes:__eventLatency.decodes,uploads:__eventLatency.uploads,
                      pixel:__eventLatency.pixel};}''')
                    events=value['events'];start=next((row['at'] for row in events if row['kind'] in
                        ('pointerup','keydown')),events[0]['at'])
                    layer_event=next((row for row in events if row['kind']=='maps.layers' and
                        any(image['id']==target_row['id'] and image.get('asset_id')==(
                            orange if value['pixel']['rgb'][0]>value['pixel']['rgb'][2] else blue)
                            for image in row['payload'].get('images',[]))),None)
                    record['clients'][role]={'frameFromLocalStartMs':round(value['pixel']['at']-start,2),
                        'timeOrigin':value['timeOrigin'],'localStart':start,
                        'pushToFrameMs':round(value['pixel']['at']-layer_event['at'],2) if layer_event else None,
                        'pixel':value['pixel'],'decodes':len(value['decodes']),'uploads':len(value['uploads']),
                        'fetches':[row['url'] for row in value['fetches']],
                        'timeline':[{'kind':row['kind'],'ms':round(row['at']-start,2)} for row in events]}
                origin_start=record['clients']['player']['timeOrigin']+record['clients']['player']['localStart']
                for entry in record['clients'].values():
                    entry['inputToFrameMs']=round(entry['timeOrigin']+entry['pixel']['at']-origin_start,2)
                measurements.append(record);cases.append({'case':label,'renderedClients':['gm','player']})
                diagnostics()

            def drag(x):
                hero=player.get_by_role('button',name='Token: Synthetic latency traveler',exact=True)
                expect(hero).to_be_visible();box=hero.bounding_box();at=point(player,(x+.5)*70,9.5*70)
                player.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
                player.mouse.down();player.mouse.move(at['x'],at['y'],steps=8);player.mouse.up()
                expect(hero).to_have_attribute('x',str(x*70),timeout=10_000)
                player.wait_for_function("__eventLatency.events.some(row=>row.kind==='tokens.ack')")

            for index in range(3):
                arm('orange');drag(9);collect(f'area-enter-{index}','player-release')
                arm('blue');drag(5);collect(f'area-exit-{index}','player-release')
            for index in range(2):
                for page in clients.values():
                    page.wait_for_function('performance.now()-__eventLatency.lastActivity>200')
                arm('orange')
                control=player.locator(f'[data-smart-image-id="{direct_row["id"]}"][data-smart-image-action="interact"]')
                control.focus();control.press('Enter')
                collect(f'direct-interact-{index}','player-keyboard')
                arm('orange');drag(9)
                for page in clients.values():page.evaluate('__eventLatency.finish()')
                player.wait_for_timeout(100)
                arm('blue');drag(5);collect(f'reset-after-direct-{index}','player-release')
            # Keep an explicit rapid sequence as well: its queueing remains
            # observable instead of being hidden by the isolated samples.
            arm('orange')
            control.focus();control.press('Enter')
            collect('direct-interact-rapid','player-keyboard')
            arm('orange');drag(9)
            for page in clients.values():page.evaluate('__eventLatency.finish()')
            player.wait_for_timeout(100)
            arm('blue');drag(5);collect('reset-after-direct-rapid','player-release')
            for role,page in clients.items():
                pixel=screenshot_pixel(page,target_row)
                assert pixel[2]>pixel[0]+70,(role,pixel)
                page.screenshot(path=str(output/f'final-{role}.png'))
            cases.append({'case':'gpu-probe-results-confirmed-by-final-screenshot-pixels'})
            # Compatibility mode allows recording the old visibility baseline.
            if os.environ.get('GRAVEWRIGHT_LATENCY_BASELINE')!='1':
                gm_pixel=screenshot_pixel(gm,private_row);player_pixel=screenshot_pixel(player,private_row)
                assert gm_pixel[0]>gm_pixel[2]+20,gm_pixel
                assert abs(player_pixel[0]-player_pixel[2])<70,player_pixel
                alpha=(gm_pixel[0]-player_pixel[0])/(237-player_pixel[0])
                assert .45<alpha<.65,(gm_pixel,player_pixel,alpha)
                assert all(row['id'] not in (private_row['id'],owner['id']) for row in state(player)['images'])
                marker_pixels={role:screenshot_pixel(page,owner) for role,page in clients.items()}
                assert sum(abs(a-b) for a,b in zip(marker_pixels['gm'],marker_pixels['player']))>20,marker_pixels
                expect(gm.locator(f'[data-smart-image-id="{owner["id"]}"]')).to_have_count(0)
                cases.append({'case':'empty-gm-marker-visible-faintly-on-game-without-interaction-target',
                    'pixels':marker_pixels})
                at=point(gm,private_row['x'],private_row['y']);gm.mouse.click(at['x'],at['y'])
                expect(gm.locator(f'[data-selected-object="image:{private_row["id"]}"]')).to_have_count(0)
                gm.locator('.game-menubar__layer').get_by_text('GM',exact=True).click()
                gm.mouse.click(at['x'],at['y'],button='right')
                expect(gm.locator(f'[data-selected-object="image:{private_row["id"]}"]')).to_have_count(1)
                gm.keyboard.press('Escape')
                cases.append({'case':'private-art-visible-faintly-to-gm-game-but-editable-only-in-gm',
                    'gmPixel':gm_pixel,'playerPixel':player_pixel,'observedAlpha':round(alpha,3)})
                gm.locator('.game-menubar__layer').get_by_text('Game',exact=True).click()

                # Drawing opacity compounds authored opacity, while players
                # receive neither the rectangle nor the text in their state.
                rectangle,text=str(uuid4()),str(uuid4())
                drawings=[{'id':rectangle,'kind':'rect','audience':'gm','color':'#ed7822',
                    'fill':'#ed7822','width':2,'opacity':.8,'fontSize':48,'rotation':0,
                    'points':[{'x':2100,'y':700},{'x':2240,'y':770}]},
                    {'id':text,'kind':'text','audience':'gm','color':'#ed7822','fill':'none',
                    'width':2,'opacity':.8,'fontSize':48,'rotation':0,'text':'GM ONLY',
                    'points':[{'x':2100,'y':840}]}]
                gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,
                  area:'drawings',action:'replace',data:{expected_version:a.version,rows:a.rows}})''',
                    {'scene':scene,'version':state()['drawings']['version'],'rows':drawings})
                gm.wait_for_timeout(150)
                rect_point={'x':2170,'y':735}
                rect_pixels={role:screenshot_pixel(page,rect_point) for role,page in clients.items()}
                rect_alpha=(rect_pixels['gm'][0]-rect_pixels['player'][0])/(237-rect_pixels['player'][0])
                assert .36<rect_alpha<.52,(rect_pixels,rect_alpha)
                assert not state(player)['drawings']['rows']
                cases.append({'case':'gm-drawing-authored-opacity-compounds-private-opacity',
                    'pixels':rect_pixels,'observedAlpha':round(rect_alpha,3)})
                text_pixels={}
                for role,page in clients.items():
                    top=point(page,2100,840);bottom=point(page,2340,900)
                    with Image.open(BytesIO(page.screenshot())) as shot:
                        crop=shot.convert('RGB').crop((int(top['x']),int(top['y']),int(bottom['x']),int(bottom['y'])))
                        text_pixels[role]=max(pixel[0]-pixel[2] for pixel in crop.get_flattened_data())
                assert text_pixels['gm']>35 and text_pixels['player']<20,text_pixels
                cases.append({'case':'gm-text-visible-faintly-and-absent-from-player-pixels-and-payload',
                    'redMinusBluePeak':text_pixels})

                # A native light action forces static scene rebuilding. Cached
                # ordinary images must survive without repeat art decoding.
                for page in clients.values():page.evaluate('watch=>__eventLatency.start(watch)',
                    {'x':target_row['x'],'y':target_row['y'],'color':'blue'})
                result=gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{mapId:scene,
                  area:'lights',action:'create',data:{x:1400,y:700,enabled:false}})''',scene)
                gm.wait_for_timeout(250)
                light=result['light']
                for page in clients.values():page.evaluate('__eventLatency.finish()')
                for enabled in (True,False):
                    for page in clients.values():page.evaluate('watch=>__eventLatency.start(watch)',
                        {'x':target_row['x'],'y':target_row['y'],'color':'blue'})
                    gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,
                      area:'lights',action:'update',data:{light_id:a.id,enabled:a.enabled}})''',
                        {'scene':scene,'id':light['id'],'enabled':enabled})
                    for page in clients.values():
                        page.wait_for_function('''a=>__eventLatency.events.some(row=>row.kind==='maps.layers'
                          &&row.payload.lights?.some(light=>light.id===a.id&&light.enabled===a.enabled))''',
                            arg={'id':light['id'],'enabled':enabled})
                        page.wait_for_timeout(150)
                    counts={role:page.evaluate('''()=>{__eventLatency.finish();return {decodes:__eventLatency.decodes.length,
                      artFetches:__eventLatency.fetches.filter(row=>row.url.includes('/game/map-assets/')).length};}''')
                        for role,page in clients.items()}
                    assert all(value['decodes']==value['artFetches']==0 for value in counts.values()),counts
                    assert screenshot_pixel(player,target_row)[2]>screenshot_pixel(player,target_row)[0]+70
                    cases.append({'case':'light-change-preserves-cached-ordinary-art','enabled':enabled,'counts':counts})
                for role,page in clients.items():page.screenshot(path=str(output/f'private-overlays-{role}.png'))
            diagnostics()
        except Exception:
            diagnostics()
            for role,page in clients.items():page.screenshot(path=str(output/f'failure-{role}.png'),full_page=True)
            raise
        finally:
            for context in reversed(contexts):context.close()
            browser.close()
    assert not errors,errors
    return {'passed':True,'cases':cases,'measurements':measurements,'pageErrors':errors,
        'measurement':'Browser performance.now; command/push events and first matching GPU frame; screenshot excluded.'}


if __name__=='__main__':
    harness.check_browser=check_browser
    harness.main()
