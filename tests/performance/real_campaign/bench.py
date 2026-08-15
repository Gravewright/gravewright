from __future__ import annotations

import argparse, json, math, statistics, time
from pathlib import Path
from playwright.sync_api import sync_playwright

FIXTURES = Path("tests/performance/gm_prefetch/fixtures-4601217-adaptive.json")

def pct(xs, p):
    if not xs: return 0.0
    xs=sorted(xs); return float(xs[min(len(xs)-1,max(0,math.ceil(len(xs)*p/100)-1))])

INIT = """(() => {
 window.__rc={frames:[],perf:{},long:[],hidden:document.hidden,visibilityChanges:0,over500:0,recording:false,requests:0,bytes:0};
 document.addEventListener('visibilitychange',()=>{window.__rc.visibilityChanges++;if(document.hidden)window.__rc.hidden=true});
 let last=performance.now(); requestAnimationFrame(function tick(now){if(window.__rc.recording){let d=now-last;window.__rc.frames.push(d);if(d>500)window.__rc.over500++}last=now;requestAnimationFrame(tick)});
 window.__gravewrightMeasureRender=true; window.__gravewrightPerfRecord=(n,v)=>{if(window.__rc.recording)(window.__rc.perf[n]||=[]).push(v)};
 try{new PerformanceObserver(l=>{if(window.__rc.recording)l.getEntries().forEach(e=>window.__rc.long.push(e.duration))}).observe({entryTypes:['longtask']})}catch(e){}
})()"""

def login(page, host, identity, password):
    page.goto(host+'/login'); page.fill('input[name="email"]',identity['email']); page.fill('input[name="password"]',password); page.click('button[type="submit"]'); page.wait_for_url('**/inside**'); page.goto(host+'/game'); page.wait_for_function('window.GravewrightMap?.debugSnapshot?.()?.renderer?.boardReady',timeout=120000)

def install_animated(page):
    page.evaluate("""() => {
      const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
      const store=GravewrightMap.tokenStoreFor(GravewrightMap.activeCanvas());
      for(let i=0;i<25;i++)store.set(`rc-animated-${i}`,{token_id:`rc-animated-${i}`,name:'',disposition:'hostile',hidden:false,grid_x:12+i%8,grid_y:12+Math.floor(i/8),width_cells:1,height_cells:1,asset_url:'benchmark://rc-animated',benchmark_animated:true,bars:{}});
      GravewrightMap.benchmarkSetAnimatedTokens([...store.values()],[{url:'benchmark://rc-animated',canvas}]);
      let raf; const run=now=>{const c=canvas.getContext('2d'),f=Math.sin(now/120);c.clearRect(0,0,128,128);c.fillStyle='#58d68d';c.beginPath();c.moveTo(64,20);c.lineTo(8,90+f*12);c.lineTo(120,90-f*12);c.fill();GravewrightMap.redraw();raf=requestAnimationFrame(run)};raf=requestAnimationFrame(run);window.__rcStop=()=>cancelAnimationFrame(raf);
    }""")

def move(page, x, y, zoom):
    page.evaluate("""([x,y,z])=>{const c=GravewrightMap.activeCanvas(),s=GravewrightMap.stateFor(c),r=c.getBoundingClientRect();s.zoom=z;s.offsetX=r.width/2-x*z;s.offsetY=r.height/2-y*z;GravewrightMap.scheduleViewportUpdate(c,true);GravewrightMap.redraw()}""",[x,y,zoom])

def phase(pages, duration):
    for p in pages: p.evaluate("window.__rc.frames=[];window.__rc.perf={};window.__rc.long=[];window.__rc.recording=true")
    route=[(900,900,.45),(2500,2500,.35),(4100,900,.42),(900,900,.45)]
    started=time.monotonic(); step=0
    while time.monotonic()-started < duration:
        x,y,z=route[step%len(route)];
        for i,p in enumerate(pages): move(p,x+(i%3)*35,y+(i%2)*35,z)
        step+=1; time.sleep(5)
    out=[]
    for p in pages:
        raw=p.evaluate("""() => {window.__rc.recording=false;const s=GravewrightMap.debugSnapshot();return {rc:window.__rc,snapshot:s,heap:performance.memory?.usedJSHeapSize||0,lighting:GravewrightLighting.debug()}}""")
        f=raw['rc']['frames']; perf=raw['rc']['perf']; lt=raw['rc']['long']; snap=raw['snapshot']['renderer']; stream=raw['snapshot']['metrics']
        out.append({'frames':len(f),'frame_ms_average':statistics.mean(f) if f else 0,'frame_ms_p50':pct(f,50),'frame_ms_p95':pct(f,95),'frame_ms_p99':pct(f,99),'frame_ms_max':max(f) if f else 0,'frames_over_33':sum(v>33.3 for v in f),'frames_over_50':sum(v>50 for v in f),'frames_over_100':sum(v>100 for v in f),'long_tasks':len(lt),'long_task_p95':pct(lt,95),'long_task_max':max(lt) if lt else 0,'renderer':{k:{'p50':pct(v,50),'p95':pct(v,95),'p99':pct(v,99)} for k,v in perf.items() if v},'heap_mb':raw['heap']/1048576,'resources':snap['animatedEntities'],'spatial':snap['spatialIndex'],'texture_cache':snap['textureCache'],'blob_cache':snap['blobCache'],'streaming':stream,'lighting':raw['lighting'][0] if raw['lighting'] else {},'validity':{'document_hidden':raw['rc']['hidden'],'visibility_changes':raw['rc']['visibilityChanges'],'raf_intervals_over_500ms':raw['rc']['over500']}})
    return out

def main():
    a=argparse.ArgumentParser();a.add_argument('--host',default='http://localhost:8011');a.add_argument('--duration',type=int,default=180);a.add_argument('--output',default='tests/performance/real_campaign/results/run-1');args=a.parse_args(); out=Path(args.output);out.mkdir(parents=True,exist_ok=True);fx=json.loads(FIXTURES.read_text())
    with sync_playwright() as pw:
      browsers=[];pages=[];errors=[]
      try:
       for i,identity in enumerate([fx['gm'],*fx['players']]):
        b=pw.chromium.launch(headless=False,args=['--enable-precise-memory-info','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding','--disable-background-timer-throttling']);browsers.append(b);p=b.new_page(viewport={'width':1366,'height':768});p.add_init_script(INIT);p.on('pageerror',lambda e,j=i:errors.append({'client':j,'error':str(e)}));login(p,args.host,identity,fx['password']);install_animated(p);pages.append(p)
       time.sleep(10); cold=phase(pages,args.duration); time.sleep(30); warm=phase(pages,args.duration)
       for i,p in enumerate(pages):p.screenshot(path=str(out/f'client-{i}.png'))
       payload={'benchmark':'gravewright-real-campaign-torture','version':1,'duration_seconds_per_phase':args.duration,'clients':[{'index':i,'role':'gm' if i==0 else 'player','cold':cold[i],'warm':warm[i]} for i in range(6)],'errors':errors}
       (out/'results.json').write_text(json.dumps(payload,indent=2));print(json.dumps(payload,indent=2))
      finally:
       for b in browsers:b.close()
if __name__=='__main__':main()
