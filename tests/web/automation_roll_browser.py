"""Exercise native automation roll modals and their real table dice transport.

Only synthetic static content and an in-page socket double are used. There is
no Django database, campaign, server mutation or dependency download.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import uuid

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
ASSETS = {
    f'/static/{domain}/{name}': ROOT / f'gravewright/{app}/static/{domain}/{name}'
    for app, domain, names in [
        ('maps', 'gravewright_maps', ['automation-presentation.js', 'automation-presentation.css']),
        ('table', 'gravewright_table', ['realtime.js', 'modal.js', 'window-controls.js',
                                      'content-state.js', 'permissions.css', 'window-polish.css']),
        ('modules', 'gravewright_modules', ['i18n.js', 'lifetime.js']),
        ('web', 'gravewright_web', ['escape.js', 'css/tokens.css', 'vendor/datastar-1.0.3.js']),
    ] for name in names
}
HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Automation roll modal</title>
<script id="gravewright-language" type="application/json">{"id":"en","messages":{}}</script>
<link rel="stylesheet" href="/static/gravewright_web/css/tokens.css">
<link rel="stylesheet" href="/static/gravewright_table/permissions.css">
<link rel="stylesheet" href="/static/gravewright_table/window-polish.css">
<link rel="stylesheet" href="/static/gravewright_maps/automation-presentation.css">
<style>body{margin:0;background:#101419;color:#e8e4d8;font:14px sans-serif}</style>
<script>
window.sent=[];window.sockets=[];window.handouts=[];
window.gravewrightJournals={open:id=>handouts.push(id)};
window.WebSocket=class extends EventTarget {
  static OPEN=1;readyState=1;
  constructor(){super();sockets.push(this);setTimeout(()=>this.receive('table.joined'),0)}
  send(raw){sent.push(JSON.parse(raw))}
  receive(type,payload={}){this.dispatchEvent(new MessageEvent('message',{
    data:JSON.stringify({type,payload:{tableId:'table-1',...payload}})}))}
  close(code=1000){this.readyState=3;this.dispatchEvent(new CloseEvent('close',{code}))}
};
window.receive=(type,payload)=>sockets.at(-1).receive(type,payload);
window.present=payload=>receive('automation.presentation',{
  tableId:'table-1',sceneId:'origin-scene',type:'roll',expression:'2d6+3',label:'Search',visibility:'public',...payload});
</script></head><body>
<main id="table-workspace" data-table-id="table-1" data-profile-id="profile-1" data-role="player">
  <button id="origin">Table control</button><div id="chat-log"></div>
</main>
<script type="module">
import '/static/gravewright_table/realtime.js';
import '/static/gravewright_maps/automation-presentation.js';
window.ready=true;
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ASSETS:
            asset = ASSETS[path]
            raw = asset.read_bytes()
            kind = 'text/css' if asset.suffix == '.css' else 'text/javascript'
        elif path == '/':
            raw, kind = HTML.encode('utf-8'), 'text/html'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.output or ROOT / f'data/runner/automation-roll-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors = []
    report = {'success': False, 'errors': errors}
    try:
        with sync_playwright() as playwright:
            launch = {'headless': True}
            if args.browser_executable:
                launch['executable_path'] = str(args.browser_executable)
            with playwright.chromium.launch(**launch) as browser:
                page = browser.new_page(viewport={'width': 1000, 'height': 720})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('window.ready && window.sent.some(entry=>entry.type==="chat.sync")')
                page.locator('#origin').focus()
                modal = page.locator('[data-automation-presentation]')
                page.evaluate('present({id:crypto.randomUUID(),tableId:"other-table"})')
                page.evaluate('present({id:crypto.randomUUID(),expression:"x".repeat(513)})')
                expect(modal).to_have_count(0)

                request_id = str(uuid.uuid4())
                request = {'id': request_id, 'label': '<img src=x onerror=alert(1)>'}
                page.evaluate('gravewrightRealtime.chatScope("different-current-scene")')
                page.evaluate('present', request)
                expect(modal).to_be_visible()
                expect(modal).to_have_attribute('role', 'dialog')
                expect(modal.locator('img,dialog')).to_have_count(0)
                expect(modal.locator('form > strong')).to_have_text(request['label'])
                submit = modal.locator('[data-presentation-roll-submit]')
                expect(submit).to_be_focused()
                assert page.locator('#table-workspace').evaluate('node=>node.inert')
                page.evaluate('present', request)
                expect(modal.locator('form')).to_have_count(1)
                page.keyboard.press('Tab')
                expect(modal.locator('[data-presentation-close]')).to_be_focused()
                page.keyboard.press('Shift+Tab')
                expect(submit).to_be_focused()
                page.keyboard.press('Enter')
                expect(submit).to_be_disabled()
                expect(submit).to_have_text('Rolling…')
                sent = page.evaluate('sent.filter(entry=>entry.type==="dice.roll")')
                assert len(sent) == 1, sent
                payload = sent[0]['payload']
                assert payload == {'tableId': 'table-1', 'expression': '2d6+3',
                                   'label': request['label'], 'visibility': 'public',
                                   'mapId': 'origin-scene', 'requestId': request_id}, payload
                page.evaluate('id=>receive("dice.error",{requestId:id,message:"Connection interrupted",code:"unavailable"})', request_id)
                expect(modal.locator('[role=alert]')).to_have_text('Connection interrupted')
                expect(submit).to_be_enabled()
                submit.click()
                page.evaluate('receive("session.ping")')
                sent = page.evaluate('sent.filter(entry=>entry.type==="dice.roll")')
                assert len(sent) == 3 and all(entry['payload'] == payload for entry in sent), sent
                page.evaluate('id=>receive("dice.ack",{requestId:id,message:{}})', request_id)
                expect(modal.locator('[role=status]')).to_have_text('Roll sent to chat.')
                expect(submit).to_be_disabled()

                page.evaluate('''()=>{
                  document.querySelector('#gravewright-language').textContent=JSON.stringify({id:'pt-BR',messages:{
                    'Dice roll request':'Pedido de rolagem de dados','Close':'Fechar','Roll':'Rolar',
                    'Roll sent to chat.':'Rolagem enviada ao chat.','Public':'Pública'}});
                  dispatchEvent(new Event('gravewright:locale'));
                }''')
                expect(modal).to_have_attribute('aria-label', 'Pedido de rolagem de dados')
                expect(modal.locator('[role=status]')).to_have_text('Rolagem enviada ao chat.')
                expect(modal.locator('code')).to_have_text('2d6+3')
                expect(modal.locator('form > strong')).to_have_text(request['label'])
                page.screenshot(path=str(work / 'roll-success.png'))
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                expect(page.locator('#origin')).to_be_focused()
                assert not page.locator('#table-workspace').evaluate('node=>node.inert')

                # Closing a pending request releases the form; a late committed
                # dice receipt must neither reopen it nor affect another request.
                pending_id = str(uuid.uuid4())
                page.evaluate('present', {'id': pending_id, 'visibility': 'gm'})
                expect(modal.locator('.automation-presentation__audience')).to_have_text('To GM')
                modal.locator('[data-presentation-roll-submit]').click()
                page.keyboard.press('Escape')
                page.evaluate('id=>receive("dice.ack",{requestId:id,message:{}})', pending_id)
                expect(modal).to_have_count(0)
                page.evaluate('present', {'id': str(uuid.uuid4()), 'type': 'message', 'text': 'Authored message'})
                expect(modal.locator('p')).to_have_text('Authored message')
                page.keyboard.press('Escape')
                page.evaluate('present', {'id': str(uuid.uuid4()), 'type': 'handout', 'journalId': 'quest-journal'})
                assert page.evaluate('handouts') == ['quest-journal']

                page.set_viewport_size({'width': 360, 'height': 640})
                page.evaluate('present', {'id': str(uuid.uuid4()), 'expression': '1d6+' * 127 + '1d6', 'label': 'L' * 48})
                expect(modal).to_be_visible()
                box = modal.bounding_box()
                assert box and box['x'] >= 0 and box['x'] + box['width'] <= 360, box
                assert modal.evaluate('node=>node.scrollWidth<=node.clientWidth'), 'No horizontal overflow'
                page.screenshot(path=str(work / 'roll-mobile.png'))
                page.evaluate('window.prunedCard=document.querySelector("[data-presentation-roll]")')
                page.evaluate('()=>{for(let i=0;i<24;i++)present({id:crypto.randomUUID(),label:`Request ${i}`})}')
                expect(modal.locator('form')).to_have_count(20)
                before = page.evaluate('sent.filter(entry=>entry.type==="dice.roll").length')
                page.evaluate('prunedCard.dispatchEvent(new Event("submit",{cancelable:true}))')
                assert page.evaluate('sent.filter(entry=>entry.type==="dice.roll").length') == before
                page.evaluate('dispatchEvent(new PageTransitionEvent("pagehide",{persisted:false}))')
                expect(modal).to_have_count(0)
                page.evaluate('present({id:crypto.randomUUID()})')
                expect(modal).to_have_count(0)
                assert not errors, errors
                report.update(success=True, checks=['explicit consent', 'safe authored text', 'deduplication',
                    'scene binding', 'retry identity', 'socket retry', 'focus and Escape', 'localization',
                    'late receipt disposal', 'existing message and journal behavior', 'mobile long content',
                    'bounded history', 'page disposal'])
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
