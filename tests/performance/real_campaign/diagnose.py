from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from bench import INIT, install_animated, login, pct

fx=json.loads(Path('tests/performance/gm_prefetch/fixtures-4601217-adaptive.json').read_text())
variants={
 'full_after_light_culling':'',
}
out={}
with sync_playwright() as pw:
 for name,setup in variants.items():
  b=pw.chromium.launch(headless=False,args=['--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding','--disable-background-timer-throttling']);p=b.new_page(viewport={'width':1366,'height':768});p.add_init_script(INIT);login(p,'http://localhost:8011',fx['gm'],fx['password']);install_animated(p);p.wait_for_timeout(5000);p.evaluate(setup);p.evaluate('window.__rc.frames=[];window.__rc.perf={};window.__rc.long=[];window.__rc.recording=true');p.wait_for_timeout(15000);raw=p.evaluate('()=>{window.__rc.recording=false;return window.__rc}');out[name]={'frame_p50':pct(raw['frames'],50),'frame_p95':pct(raw['frames'],95),'app_render_p95':pct(raw['perf'].get('app_render',[]),95),'prepare_p95':pct(raw['perf'].get('render_prepare',[]),95),'long_tasks':len(raw['long']),'over500':raw['over500']};b.close()
print(json.dumps(out,indent=2));Path('tests/performance/real_campaign/results/diagnostic-components.json').write_text(json.dumps(out,indent=2))
