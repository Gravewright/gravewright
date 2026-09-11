"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/journals.py --original /path/to/reference
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
    output = ROOT / 'test-results' / 'journals'
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
                                body={'journal_id':journal_state['journals'][0]['id']}
                            elif action=='update':
                                payload=route.request.post_data_json
                                j=next(j for j in journal_state['journals'] if j['id']==payload['journal_id'])
                                j.update(title=payload['title'],visibility=payload['visibility'],content_doc=payload['data']['content'],editable_sections=payload['data']['sections'],sections=payload['data']['sections'],diary={'gm':payload['data'].get('gm')})
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
                expect(page.locator('#journals-panel')).to_be_visible()
                capture('directory')
                both('Create journal')
                expect(page.get_by_role('dialog',name='Create journal',exact=True)).to_be_visible()
                capture('create')
                page.get_by_role('dialog',name='Create journal',exact=True).locator('input').fill('The Chronicle')
                if reference:reference.get_by_role('dialog',name='Create journal',exact=True).locator('input').fill('The Chronicle')
                page.get_by_role('dialog',name='Create journal',exact=True).get_by_role('button',name='Create journal',exact=True).click()
                notebook=page.locator('.journal-window')
                expect(notebook).to_be_visible()
                journal_state=page.request.get(base+'/api/containers/'+rows[0]['id']+'/journals').json()
                if reference:reference.get_by_role('dialog',name='Create journal',exact=True).get_by_role('button',name='Create journal',exact=True).click()
                if reference:expect(reference.locator('.journal-window')).to_be_visible()
                capture('empty-notebook')
                def action(name):
                    notebook.get_by_role('button',name=name,exact=True).click()
                    if reference:reference.locator('.journal-window').get_by_role('button',name=name,exact=True).click()
                action('New text page')
                expect(notebook.get_by_role('textbox',name='Page content')).to_be_visible()
                capture('text-page')
                notebook.get_by_role('textbox',name='Page content').fill('A meeting at the old inn.')
                if reference:reference.get_by_role('textbox',name='Page content').fill('A meeting at the old inn.')
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                if reference:expect(reference.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                capture('written-page')
                action('Read')
                capture('reading')
                action('Edit')
                action('GM area')
                notebook.get_by_role('textbox',name='GM notes',exact=True).fill('The host is a spy.')
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                notebook.get_by_role('button',name='Close journal',exact=True).click()
                expect(notebook).to_have_count(0)
                page.get_by_role('button',name='The Chronicle',exact=True).click()
                expect(notebook.get_by_role('textbox',name='Page content')).to_have_text('A meeting at the old inn.')
                # Public access never exposes the GM area to a player.
                notebook.get_by_role('button',name='Permissions',exact=True).click()
                notebook.locator('[name=visibility]').select_option('shared')
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                player_context=browser.new_context(viewport={'width':1440,'height':1000})
                player=player_context.new_page();player.on('pageerror',lambda e:errors.append(str(e)))
                player.goto(base+'/register');player.locator('#owner-name').fill('Browser Player');player.locator('#owner-email').fill('player@example.test');player.locator('#owner-password').fill(PASSWORD)
                player.get_by_role('button',name='Create my account',exact=True).click()
                player.get_by_placeholder('XXXX-XXXX',exact=True).fill(invitation);player.get_by_role('button',name='Join a table',exact=True).click();player.get_by_role('button',name='Open The Lost Keep',exact=True).click();player.get_by_role('button',name='Enter table',exact=True).click();seated(player)
                player.get_by_role('button',name='Journals',exact=True).click();player.get_by_role('button',name='The Chronicle',exact=True).click()
                expect(player.locator('.journal-window')).to_be_visible()
                assert 'The host is a spy.' not in player.content()
                expect(player.locator('.journal-window').get_by_role('button',name='Edit',exact=True)).to_have_count(0)
                notebook.locator('[name=visibility]').select_option('private')
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                expect(player.locator('.journal-window')).to_have_count(0)
                expect(player.get_by_role('button',name='The Chronicle',exact=True)).to_have_count(0)
                # Images and PDF are stored privately and render within their pages.
                notebook.get_by_role('button',name='New image page',exact=True).click()
                notebook.locator('.diary-workspace__upload input').set_input_files({'name':'map.png','mimeType':'image/png','buffer':cover_file.getvalue()})
                expect(notebook.locator('.diary-workspace__image')).to_be_visible()
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                notebook.get_by_role('button',name='New PDF page',exact=True).click()
                notebook.locator('.diary-workspace__upload input').set_input_files({'name':'chronicle.pdf','mimeType':'application/pdf','buffer':sample_pdf()})
                expect(notebook.locator('.journal-pdf canvas')).to_be_visible(timeout=15000)
                expect(notebook.locator('[data-pdf-count]')).to_have_text('1 / 2')
                notebook.get_by_role('button',name='Next PDF page',exact=True).click()
                expect(notebook.locator('[data-pdf-count]')).to_have_text('2 / 2')
                notebook.get_by_role('searchbox',name='Search PDF',exact=True).fill('Chronicle')
                notebook.get_by_role('button',name='Search PDF',exact=True).click()
                expect(notebook.locator('[data-pdf-count]')).to_have_text('1 / 2')
                expect(notebook.locator('.journal-window__save')).to_have_text('Saved',timeout=10000)
                with page.expect_popup() as info:notebook.get_by_role('button',name='Detach window',exact=True).click()
                popup=info.value;expect(popup.locator('.journal-window')).to_be_visible();popup.close();expect(notebook).to_be_visible()
                notebook.get_by_role('button',name='Minimize',exact=True).click();expect(notebook.locator('.journal-window__body')).to_be_hidden()
                notebook.get_by_role('button',name='Minimize',exact=True).click();expect(notebook.locator('.journal-window__body')).to_be_visible()
                notebook.get_by_role('button',name='Close journal',exact=True).click()
                page.get_by_role('button',name='Create folder',exact=True).click()
                folder_dialog=page.get_by_role('dialog',name='Journal folder',exact=True)
                folder_dialog.locator('[name=name]').fill('Places')
                folder_dialog.get_by_role('button',name='Save folder',exact=True).click()
                expect(page.locator('#journals-panel .gw-folder__label')).to_have_text('Places')
                page.locator('#journals-panel .gw-folder__actions button[title="Create journal"]').click()
                create_dialog=page.get_by_role('dialog',name='Create journal',exact=True)
                create_dialog.locator('input').fill('The village')
                create_dialog.get_by_role('button',name='Create journal',exact=True).click()
                expect(page.locator('.journal-window')).to_be_visible()
                persisted=page.request.get(base+'/api/containers/'+rows[0]['id']+'/journals').json()
                assert next(j for j in persisted['journals'] if j['title']=='The village')['folder_id'] == persisted['folders'][0]['id']
                assert not errors,errors
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser journal editing, privacy and window flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
