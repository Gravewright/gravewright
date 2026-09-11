"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/journal_types.py --original /path/to/reference
Uses a temporary database; never creates accounts in the development database.
"""
import argparse
import functools
import json
from io import BytesIO
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = 'browser-password-123'


def sample_pdf():
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
             b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
             b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for text in [b'Chronicle',b'The archive']:
        stream=b'BT /F1 18 Tf 20 240 Td ('+text+b') Tj ET'
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    output=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,body in enumerate(objects,1):
        offsets.append(len(output));output.extend(str(i).encode()+b' 0 obj\n'+body+b'\nendobj\n')
    start=len(output);output.extend(b'xref\n0 8\n0000000000 65535 f \n')
    for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(b'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n')
    return bytes(output)


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path)
    args = parser.parse_args()
    output = ROOT / 'test-results' / 'journal-types'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='grave-table-browser-') as temp:
        env = {**os.environ, 'GRAVEWRIGHT_DATABASE': str(Path(temp) / 'browser.sqlite3'), 'GRAVEWRIGHT_MEDIA_ROOT': str(Path(temp) / 'media')}
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=ROOT, env=env,
                       check=True, stdout=subprocess.DEVNULL)
        address = f'127.0.0.1:{port()}'
        base = f'http://{address}'
        log = (output / 'server.log').open('w')
        server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', address, '--noreload'],
                                  cwd=ROOT, env=env, stdout=log, stderr=log)
        reference_server = None
        try:
            for _ in range(100):
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Django did not start; inspect test-results/realtime/server.log')
            if args.original:
                handler = functools.partial(QuietHandler, directory=str(args.original / 'dist/frontend'))
                reference_server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
                threading.Thread(target=reference_server.serve_forever, daemon=True).start()
                reference_url = f'http://127.0.0.1:{reference_server.server_port}'
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(viewport={'width': 1440, 'height': 1000},reduced_motion='reduce')
                context.add_init_script("window.__sockets=[]; const Native=window.WebSocket; window.WebSocket=class extends Native{constructor(...args){super(...args);window.__sockets.push(this)}}")
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                reference = None
                account = {'name':'Browser Owner','email':'owner@example.test','role':'owner'}
                rows = []
                temporary_code = ''
                journal_state={'journals':[],'folders':[],'members':[],'is_gm':True,'handouts_enabled':True}
                online_members = [{'id':'owner', 'name':'Browser Owner','role':'gm'}]
                reference_sockets = []
                cover_file = BytesIO()
                Image.new('RGB', (640,360), '#354b66').save(cover_file, 'PNG')
                page.goto(base)
                page.locator('#owner-name').fill(account['name'])
                page.locator('#owner-email').fill(account['email'])
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button', name='Create administrator').click()
                expect(page.locator('#inside-shell')).to_be_visible()
                if reference_server:
                    reference = browser.new_page(viewport={'width': 1440, 'height': 1000},reduced_motion='reduce')
                    def mock_auth(route):
                        path = route.request.url.split(reference_url)[-1].split('?')[0]
                        if path.endswith('/journals'):
                            body=journal_state
                        elif '/library/journals/' in path:
                            action=path.rsplit('/',1)[-1]
                            if action=='create':
                                body={'journal_id':next(j['id'] for j in journal_state['journals'] if j['title']==route.request.post_data_json['title'])}
                            elif action=='update':
                                payload=route.request.post_data_json
                                j=next(j for j in journal_state['journals'] if j['id']==payload['journal_id'])
                                j.update(title=payload['title'],visibility=payload['visibility'])
                                if j['type']=='quest':
                                    j['quest']=payload['data']
                                    j['quest']['display_objectives']=[r for r in j['quest']['objectives'] if r['visibleToPlayers']]
                                    j['quest']['display_rewards']=[r for r in j['quest']['rewards'] if r['visibleToPlayers']]
                                elif j['type']=='roll_table':j['roll_table']=payload['data']
                                body={'journal_id':j['id']}
                            else: body={}
                        elif path.endswith('/status'):
                            body = {'configured': True}
                        elif path.endswith('/session'):
                            body = {'authenticated': True, 'account':account}
                        elif path == '/api/containers':
                            body = rows
                        elif path == '/api/rulesets':
                            body = {'rulesets':[{'systemId':'gravewright-pdf-system','title':'Gravewright PDF System','actorTypes':[{'id':'character','label':'Character'}]}]}
                        elif path.endswith('/map'):
                            body = None
                        elif path.endswith('/modules'):
                            body = {'modules':[], 'moduleSetRevision':'1','tableId':rows[0]['id'],'replacements':{}}
                        elif path.endswith('/capabilities'):
                            body = {'items':False}
                        elif path.endswith(('/blocks','/scene-directory','/folders','/journals')):
                            body = []
                        elif path == '/api/player-preferences':
                            body = {'pingColor':'#f2c679'}
                        elif path.endswith('/invitation') or path.endswith('/removal-code'):
                            body = {'code':temporary_code, 'expiresAt':9999999999999}
                        else:
                            body = {'ready': True, 'token': 'reference'}
                        route.fulfill(status=200, json=body)
                    reference.route('**/campaigns/*/cover', lambda route: route.fulfill(content_type='image/png',body=cover_file.getvalue()))
                    def mock_socket(ws):
                        reference_sockets.append(ws)
                        def received(raw):
                            message=json.loads(raw)
                            if message['type']=='table.join':
                                ws.send(json.dumps({'type':'table.joined','payload':{'tableId':rows[0]['id'],'role':'gm'}}))
                                ws.send(json.dumps({'type':'table.presence','payload':{'members':online_members}}))
                        ws.on_message(received)
                    reference.route_web_socket('**/ws', mock_socket)
                    reference.route('**/api/**', mock_auth)
                    reference.route('**/__gravewright/csrf', mock_auth)
                    reference.goto(reference_url)
                    expect(reference.locator('.gw-shell')).to_be_visible()

                def capture(name):
                    if name=='quest-gm':
                        (output/'gm-django.html').write_text(page.locator('.quest-sheet').inner_html())
                        if reference:(output/'gm-original.html').write_text(reference.locator('.quest-sheet').inner_html())
                    for width, height in [(1440, 1000), (390, 844)]:
                        label = f'{name}-{width}'
                        # Reflow both pages from the same viewport to normalize cached
                        # compositor layers after a modal changes height.
                        page.set_viewport_size({'width': width+1, 'height': height})
                        page.set_viewport_size({'width': width, 'height': height})
                        page.mouse.move(0, 0)
                        page.evaluate('document.activeElement?.blur()')
                        # Let CSS transitions settle after mouse/focus changes.
                        page.wait_for_timeout(250)
                        target = output / f'{label}-django.png'
                        page.screenshot(path=str(target), full_page=True, animations='disabled', caret='hide')
                        if reference:
                            reference.set_viewport_size({'width': width+1, 'height': height})
                            reference.set_viewport_size({'width': width, 'height': height})
                            reference.mouse.move(0, 0)
                            reference.evaluate('document.activeElement?.blur()')
                            reference.wait_for_timeout(250)
                            original = output / f'{label}-original.png'
                            reference.screenshot(path=str(original), full_page=True, animations='disabled', caret='hide')
                            a, b = Image.open(target).convert('RGB'), Image.open(original).convert('RGB')
                            assert a.size == b.size, (label, a.size, b.size)
                            difference = ImageChops.difference(a, b)
                            changed = sum(1 for pixel in difference.get_flattened_data() if max(pixel) > 8)
                            ratio = changed / (a.width * a.height)
                            difference.save(output / f'{label}-diff.png')
                            report.append({'screen': label, 'changed_pixel_ratio': ratio,
                                           'exact_match': difference.getbbox() is None})
                            print(label, f'{ratio:.6%} pixels differ', flush=True)
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    if reference:
                        reference.set_viewport_size({'width': 1440, 'height': 1000})

                def both(name):
                    page.get_by_role('button',name=name,exact=True).click()
                    if reference:
                        reference.get_by_role('button',name=name,exact=True).click()

                def post(target_page,path,data):
                    token=next(c['value'] for c in target_page.context.cookies() if c['name']=='gravewright-csrf')
                    return target_page.request.post(base+path,data=data,headers={'X-CSRF-Token':token})

                def seated(target):
                    expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence','seated',timeout=15000)

                def echo(text,name,identifier):
                    if reference:
                        reference_sockets[-1].send(json.dumps({'type':'chat.message','payload':{'id':str(identifier),'mapId':'','tableId':rows[0]['id'],'from':{'name':name},'text':text,'at':identifier}}))

                page.get_by_role('button',name='Begin my first journey').click()
                page.get_by_placeholder('Campaign name').fill('The Lost Keep')
                page.get_by_role('button',name='Create table',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                rows=page.request.get(base+'/api/containers').json()
                invitation=post(page,'/api/containers/'+rows[0]['id']+'/invitation',{}).json()['code']
                page.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                page.get_by_role('button',name='Enter table',exact=True).click()
                seated(page)
                if reference:
                    reference.reload()
                    reference.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                    reference.get_by_role('button',name='Enter table',exact=True).click()
                    seated(reference)
                both('Journals')
                def sync_reference():
                    nonlocal journal_state
                    journal_state=page.request.get(base+'/api/containers/'+rows[0]['id']+'/journals').json()
                    if reference:
                        reference_sockets[-1].send(json.dumps({'type':'journal.updated','payload':{}}))
                        reference.wait_for_timeout(200)
                def create(kind,title):
                    both('Create journal')
                    dialog=page.get_by_role('dialog',name='Create journal',exact=True)
                    dialog.locator('input').fill(title);dialog.locator('select').select_option(kind)
                    dialog.locator('button[type=submit]').click()
                    expect(page.locator('.journal-window')).to_be_visible()
                    sync_reference()
                    if reference:
                        dialog=reference.get_by_role('dialog',name='Create journal',exact=True)
                        dialog.locator('input').fill(title);dialog.locator('select').select_option(kind)
                        dialog.locator('button[type=submit]').click()
                        expect(reference.locator('.journal-window')).to_be_visible()
                def action(name):
                    page.locator('.journal-window').get_by_role('button',name=name,exact=True).click()
                    if reference:reference.locator('.journal-window').get_by_role('button',name=name,exact=True).click()
                def fill(label,value):
                    page.locator('.journal-window').get_by_role('textbox',name=label,exact=True).fill(value)
                    if reference:reference.locator('.journal-window').get_by_role('textbox',name=label,exact=True).fill(value)
                def saved():
                    expect(page.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                    if reference:expect(reference.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                create('quest','The missing courier')
                capture('quest-read-empty');action('Edit');capture('quest-content')
                fill('Location','Old road');fill('Quest giver','The innkeeper');fill('Summary','Find the missing courier.')
                fill('Quest description','Follow the northern road.');saved();capture('quest-written')
                action('Objectives');action('Add');fill('Objective','Find the courier');saved();capture('quest-objectives')
                action('Rewards');action('Add');fill('Reward','Twenty coins');saved();capture('quest-rewards')
                action('GM area');fill('GM notes','A secret ambush.');saved();capture('quest-gm')
                action('Read');capture('quest-read');action('Close journal')
                create('quest_board','Village notices');capture('board-empty');action('Edit');capture('board-edit')
                sync_reference()
                quest_id=next(j['id'] for j in journal_state['journals'] if j['type']=='quest')
                page.get_by_role('combobox',name='Quest to add').select_option(quest_id)
                page.locator('.quest-board__add').get_by_role('button',name='Add',exact=True).click()
                expect(page.locator('.quest-board__title')).to_have_text('The missing courier')
                sync_reference()
                if reference:
                    expect(reference.locator('.quest-board__title')).to_have_text('The missing courier')
                capture('board-linked');action('Read');capture('board-wall');action('Close journal')
                create('roll_table','Road encounters');capture('table-empty');action('Edit');action('Add entry')
                fill('Entry name','Courier');fill('Result','The courier is waiting beside a cart.')
                page.get_by_role('spinbutton',name='Weight',exact=True).fill('3')
                if reference:reference.get_by_role('spinbutton',name='Weight',exact=True).fill('3')
                saved();capture('table-edit');action('Read');capture('table-read')
                # Server draw, shared chat, exhaustion and reset.
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('With replacement',exact=True).uncheck()
                expect(page.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                page.get_by_role('button',name='Roll',exact=True).click()
                expect(page.locator('.journal-window__result')).to_have_text('Courier: The courier is waiting beside a cart.')
                expect(page.get_by_role('button',name='Roll',exact=True)).to_be_disabled()
                page.get_by_role('button',name='Reset results',exact=True).click()
                expect(page.get_by_role('button',name='Roll',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Chat',exact=True).click()
                expect(page.locator('#chat-panel')).to_contain_text('Road encounters — Courier: The courier is waiting beside a cart.')
                page.get_by_role('button',name='Close journal',exact=True).click()
                # A player sees a board's public quest read-only without a sidebar grant.
                sync_reference()
                board_id=next(j['id'] for j in journal_state['journals'] if j['type']=='quest_board')
                board=next(j for j in journal_state['journals'] if j['id']==board_id)
                page.evaluate("p=>window.gravewrightRealtime.journalCommand('update',p)",{'journal_id':board_id,'title':board['title'],'visibility':'shared','version':board['version'],'data':{}})
                player_context=browser.new_context(viewport={'width':1440,'height':1000})
                player=player_context.new_page();player.goto(base+'/register');player.locator('#owner-name').fill('Browser Player');player.locator('#owner-email').fill('player@example.test');player.locator('#owner-password').fill(PASSWORD)
                player.get_by_role('button',name='Create my account',exact=True).click()
                player.get_by_placeholder('XXXX-XXXX',exact=True).fill(invitation);player.get_by_role('button',name='Join a table',exact=True).click();player.get_by_role('button',name='Open The Lost Keep',exact=True).click();player.get_by_role('button',name='Enter table',exact=True).click();seated(player)
                player.get_by_role('button',name='Journals',exact=True).click();player.get_by_role('button',name='Village notices',exact=True).click()
                expect(player.locator('.directory-entry')).to_have_count(1)
                player.locator('.quest-board__notice').click()
                quest_window=player.locator('[data-journal-type=quest]')
                expect(quest_window).to_be_visible();expect(quest_window.get_by_role('button',name='Edit',exact=True)).to_have_count(0)
                assert 'A secret ambush.' not in player.content()
                page.evaluate("p=>window.gravewrightRealtime.journalCommand('board-remove',p)",{'journal_id':board_id,'quest_id':quest_id})
                expect(quest_window).to_have_count(0);expect(player.locator('.quest-board__notice')).to_have_count(0)
                assert not errors,errors
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser quest, board and roll-table flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
