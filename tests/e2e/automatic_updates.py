"""Isolated cross-platform managed upgrade, HTTPS checksum and rollback acceptance test.
Run with the project's Python environment. Uses uv's cached dependencies.
"""
import functools
import hashlib
import http.server
import os
from pathlib import Path
import socket
import ssl
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    global ROOT
    source_root = ROOT
    work = Path(tempfile.mkdtemp(prefix='gravewright-auto-update-'))
    ROOT = work / 'application'
    shutil.copytree(source_root, ROOT, ignore=shutil.ignore_patterns(
        '.git', '.venv', 'node_modules', '__pycache__', '.env', 'data', 'media', 'staticfiles', 'test-results'))
    sys.path.insert(0, str(ROOT))
    print('Isolated workspace:', work, flush=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    os.environ.update(GRAVEWRIGHT_HOST='127.0.0.1',GRAVEWRIGHT_PORT=str(port))
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', GRAVEWRIGHT_DATABASE=str(work/'db.sqlite3'), GRAVEWRIGHT_MEDIA_ROOT=str(work/'media'), GRAVEWRIGHT_CONTENT_ROOT=str(work/'compendiums'))
    if '--runner' in sys.argv:
        from scripts.gravewright_runner import prepare_environment
        directory = work / 'user-data'; directory.mkdir()
        prepare_environment(directory, port)
        from scripts.windows.create_runner import create_runner
        create_runner(ROOT, sys.executable, directory, shutil.which('uv'))
        original_runner = (ROOT / 'Gravewright Runner.bat').read_bytes()
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connections
    from gravewright.accounts.models import User
    from scripts.update_supervisor import Supervisor, read, download
    call_command('migrate', interactive=False, verbosity=0)
    User.objects.create_user(name='Preserved owner',email='upgrade@example.test',password='upgrade-test-password',role='owner')
    from django.conf import settings
    media=Path(settings.MEDIA_ROOT);media.mkdir();(media/'fixture').write_bytes(b'preserved')
    content=Path(settings.GRAVEWRIGHT_CONTENT_ROOT);content.mkdir();(content/'fixture').write_bytes(b'preserved')
    # An enabled marketplace app must survive environment rebuilds and rollback.
    import io
    import json
    from importlib.metadata import version as dependency_version
    from gravewright.modules.packages import host
    from gravewright.modules.server_apps import plan
    from scripts.update_supervisor import write
    raw = io.BytesIO()
    manifest = {'id': 'test.update', 'name': 'Update fixture', 'version': '1.0.0',
                'description': '', 'author': 'Tests', 'license': 'MIT',
                'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
                'django': {'apps': ['update_fixture'], 'requirements': ['jsonschema==' + dependency_version('jsonschema')]}}
    with zipfile.ZipFile(raw, 'w') as archive_file:
        archive_file.writestr('manifest.json', json.dumps(manifest))
        archive_file.writestr('update_fixture/__init__.py', '')
        archive_file.writestr('update_fixture/apps.py', 'from django.apps import AppConfig\nclass FixtureConfig(AppConfig):\n name="update_fixture"\n gravewright_urlconf="update_fixture.urls"\n')
        archive_file.writestr('update_fixture/urls.py', 'from django.http import HttpResponse\nfrom django.urls import path\nurlpatterns=[path("__update_fixture",lambda request: HttpResponse("preserved"))]\n')
    host().install_local(raw.getvalue())
    write(host().directory / 'server-apps.json', plan('test.update', '1.0.0', True))
    connections.close_all()
    supervisor=Supervisor(ROOT,work/'state',settings.DATABASES['default']['NAME'],media,'127.0.0.1',port)
    files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=source_root).decode().split('\0')
    installed_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    (ROOT / 'obsolete-release-file.txt').write_text('remove on upgrade', encoding='utf-8')
    (ROOT / '.env').write_text('# local configuration must survive\n', encoding='utf-8')
    def archive(sequence, failure=None):
        target=work/f'alpha{sequence}.zip'
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for name in files:
                file=source_root/name
                if not name or not file.is_file():continue
                data=file.read_bytes()
                if name in ('pyproject.toml','uv.lock'):
                    data=data.replace(f'version = "{installed_version}"'.encode(), f'version = "0.1.0a{sequence}"'.encode())
                if name=='config/managed_asgi.py' and failure=='startup':
                    data=b"raise RuntimeError('Intentional startup failure')\n"+data
                if name in ('Install Windows.bat', 'scripts/windows/runner.bat'):
                    data += f'\nrem release test {sequence}\n'.encode()
                z.writestr('release/'+name,data)
            z.writestr('release/new-release-file.txt', str(sequence))
            if failure=='migration':
                z.writestr('release/gravewright/accounts/migrations/0004_update_failure.py',"from django.db import migrations\ndef fail(apps,schema_editor):\n apps.get_model('gravewright_accounts','User').objects.update(name='Should roll back')\n raise RuntimeError('Intentional migration failure')\nclass Migration(migrations.Migration):\n dependencies=[('gravewright_accounts','0003_userpreference_locale')]\n operations=[migrations.RunPython(fail)]\n")
        return target
    cert,key=work/'cert.pem',work/'key.pem'
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta, timezone
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, 'localhost')])
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                   .public_key(private.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1))
                   .not_valid_after(datetime.now(timezone.utc)+timedelta(days=1))
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False)
                   .sign(private, hashes.SHA256()))
    cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(work)))
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key);server.socket=context.wrap_socket(server.socket,server_side=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    import urllib.request
    client_context=ssl.create_default_context(cafile=str(cert))
    def trusted_open(request,timeout):return urllib.request.urlopen(request,timeout=timeout,context=client_context)
    def job(target,sequence):return {'version':f'0.1.0-alpha.{sequence}','artifact':{'url':f'https://localhost:{server.server_port}/{target.name}','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':target.stat().st_size}}
    def preserved():
        connections.close_all()
        assert User.objects.get().name=='Preserved owner'
        assert (media/'fixture').read_bytes()==b'preserved'
        assert (content/'fixture').read_bytes()==b'preserved'
        assert read(host().directory / 'server-apps.json')['test.update']['version'] == '1.0.0'
        if supervisor.child is not None:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/__update_fixture') as response:
                assert response.read() == b'preserved'
        connections.close_all()
    try:
        supervisor.start(ROOT);supervisor.ready()
        with patch('scripts.update_supervisor.urlopen',trusted_open):
            first=archive(1)
            invalid=job(first,1)['artifact'];invalid['sha256']='0'*64
            try:download(invalid,work/'invalid.zip',lambda *a,**k:None)
            except ValueError:pass
            else:raise AssertionError('Invalid checksum accepted')
            print('PASS: bad checksum rejected.',flush=True)
            supervisor.apply(job(first,1))
            assert read(supervisor.state/'progress.json')['stage']=='complete', (supervisor.state/'update.log').read_text()[-4000:]
            preserved();active=supervisor.active
            assert active == ROOT
            assert (ROOT / 'new-release-file.txt').read_text() == '1'
            assert not (ROOT / 'obsolete-release-file.txt').exists()
            assert 'release test 1' in (ROOT / 'Install Windows.bat').read_text()
            assert (ROOT / '.env').read_text() == '# local configuration must survive\n'
            old = ROOT.with_name(ROOT.name + '.old')
            assert (old / 'obsolete-release-file.txt').is_file()
            assert (old / '.gravewright-rollback/database.sqlite3').is_file()
            if '--runner' in sys.argv:
                assert any('release test 1' in p.read_text() for p in (directory / '.runner-launchers').glob('*.bat'))
                assert supervisor.python(ROOT) in (ROOT / 'Gravewright Runner.bat').read_text()
            print('PASS: in-place replacement, new/removed files, updated BATs, preserved .env and retained .old.',flush=True)
            for failure in ['migration','startup']:
                target=archive(2,failure)
                supervisor.apply(job(target,2))
                assert read(supervisor.state/'progress.json')['stage']=='rolled_back', (supervisor.state/'update.log').read_text()[-4000:]
                assert supervisor.active==active
                assert (ROOT / 'new-release-file.txt').read_text() == '1'
                assert 'release test 1' in (ROOT / 'Install Windows.bat').read_text()
                preserved()
                assert not (supervisor.state/'maintenance').exists()
                print('PASS:',failure,'failure restores previous server, database and files.',flush=True)
            third = job(archive(3), 3)
            third['keep_old'] = False
            supervisor.apply(third)
            assert read(supervisor.state/'progress.json')['stage'] == 'complete'
            assert read(supervisor.state/'progress.json')['backup'] is None
            assert list(ROOT.parent.glob('*.old')) == [old]
            assert (ROOT / 'new-release-file.txt').read_text() == '3'
            preserved()
            supervisor.stop()
            from scripts.rollback_update import rollback
            rollback(old)
            assert not (ROOT / 'new-release-file.txt').exists()
            assert (ROOT / 'obsolete-release-file.txt').is_file()
            if '--runner' in sys.argv:
                assert (ROOT / 'Gravewright Runner.bat').read_bytes() == original_runner
            preserved()
            print('PASS: optional .old retention and explicit rollback of code and data.', flush=True)
    finally:
        supervisor.stop();server.shutdown()
    print('All managed upgrade acceptance checks passed. No real installation data changed.',flush=True)


if __name__=='__main__':main()
