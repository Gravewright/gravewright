"""Measure the isolated performance_server.py fixture; --baseline [revision] compares Git assets."""
import json
import sys
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'
metrics = {}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**SEED['sessions'][0], 'url': BASE}])
    page = context.new_page()
    if '--baseline' in sys.argv:
        # Compare the same fixture with the committed assets before this change.
        position=sys.argv.index('--baseline')+1
        revision=sys.argv[position] if position<len(sys.argv) else 'HEAD'
        for asset in ['gravewright_maps/vendor/board.js','gravewright_maps/tools.js',
                      'gravewright_tokens/controller.js','gravewright_tokens/workspace.js']:
            app=asset.split('/')[0].removeprefix('gravewright_')
            path=f'gravewright/{app}/static/{asset}'
            body=subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=ROOT)
            page.route(f'**/static/{asset}*',lambda route,_request,body=body:route.fulfill(body=body,content_type='text/javascript'))
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    images = []
    page.on('request', lambda request: images.append(request.url) if '/game/map-assets/' in request.url else None)
    page.add_init_script("""window.perfStats={nodes:0,longTasks:[],gpuClears:0};
      for(const method of ['createElement','createElementNS']){const original=document[method];
        document[method]=function(...args){perfStats.nodes++;return original.apply(this,args)}}
      new PerformanceObserver(list=>perfStats.longTasks.push(...list.getEntries().map(e=>e.duration)))
        .observe({type:'longtask',buffered:true});
      for(const name of ['WebGLRenderingContext','WebGL2RenderingContext']){
        const proto=window[name]?.prototype;if(!proto)continue;const clear=proto.clear;
        proto.clear=function(...args){perfStats.gpuClears++;return clear.apply(this,args)};
      }""")
    cdp = context.new_cdp_session(page)
    cdp.send('Performance.enable')
    def sample():
        return {m['name']: m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
    page.goto(f'{BASE}/game/{SEED["campaign"]}', wait_until='domcontentloaded')
    page.wait_for_function("Boolean(window.gravewrightMaps?.board && document.querySelectorAll('.token-workspace rect[role=button]').length>=30)")
    page.wait_for_timeout(1000)  # Let initial image decoding settle before measuring gestures.
    metrics['initial_image_requests'] = len(images)
    def measure(name, run):
        before = sample(); count = len(images)
        nodes = page.evaluate('perfStats.nodes'); long_tasks = page.evaluate('perfStats.longTasks.length')
        clears = page.evaluate('perfStats.gpuClears')
        run()
        page.wait_for_timeout(500)
        after = sample()
        metrics[name] = {'task_ms': round(1000*(after['TaskDuration']-before['TaskDuration']),1),
            'script_ms': round(1000*(after['ScriptDuration']-before['ScriptDuration']),1),
            'created_nodes': page.evaluate('perfStats.nodes')-nodes,
            'image_requests':len(images)-count,
            'gpu_clears':page.evaluate('perfStats.gpuClears')-clears,
            'long_tasks':page.evaluate('perfStats.longTasks.length')-long_tasks}
    def hover():
        page.mouse.move(200,100)
        page.mouse.move(1200,800,steps=40)
    measure('idle',lambda:page.wait_for_timeout(1000))
    measure('hover', hover)
    def pan():
        page.mouse.move(600,400);page.mouse.down(button='middle')
        page.mouse.move(680,460,steps=24);page.mouse.up(button='middle')
    measure('pan', pan)
    page.locator('.game-menubar__layer').nth(2).click()
    image = page.locator('.image-workspace__image').nth(21)
    expect(image).to_be_visible();image.click()
    handle = page.locator('.image-workspace__resize').nth(2)
    expect(handle).to_be_visible()
    def resize():
        box=handle.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
        page.mouse.move(x,y);page.mouse.down()
        page.mouse.move(x+50,y+30,steps=24);page.keyboard.press('Escape');page.mouse.up()
    measure('image_resize_cancel',resize)
    page.locator('.game-menubar__layer').nth(0).click()
    def token_drag():
        token=page.locator('.token-workspace rect[role=button]').first
        box=token.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y+20,steps=24)
        page.keyboard.press('Escape');page.mouse.up()
    measure('token_drag_cancel',token_drag)
    if '--baseline' not in sys.argv:
        assert metrics['initial_image_requests'] == 1, metrics
        assert metrics['image_resize_cancel']['image_requests'] == 0, metrics
        assert metrics['idle']['gpu_clears'] <= 2, metrics
    assert not errors, errors
    browser.close()
output=ROOT/'data'/f'ingame-performance-{sys.argv[1] if len(sys.argv)>1 else "sample"}.json'
output.write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print(json.dumps(metrics,indent=2))
