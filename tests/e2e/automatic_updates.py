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
    work = Path(tempfile.mkdtemp(prefix='gravewright-auto-update-'))
    print('Isolated workspace:', work, flush=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    os.environ.update(GRAVEWRIGHT_HOST='127.0.0.1',GRAVEWRIGHT_PORT=str(port))
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', GRAVEWRIGHT_DATABASE=str(work/'db.sqlite3'), GRAVEWRIGHT_MEDIA_ROOT=str(work/'media'), GRAVEWRIGHT_CONTENT_ROOT=str(work/'compendiums'))
    if '--runner' in sys.argv:
        from scripts.gravewright_runner import prepare_environment
        directory = work / 'user-data'; directory.mkdir()
        prepare_environment(directory, port)
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
    connections.close_all()
    supervisor=Supervisor(ROOT,work/'state',settings.DATABASES['default']['NAME'],media,'127.0.0.1',port)
    files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    installed_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    def archive(sequence, failure=None):
        target=work/f'alpha{sequence}.zip'
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for name in files:
                file=ROOT/name
                if not name or not file.is_file():continue
                data=file.read_bytes()
                if name in ('pyproject.toml','uv.lock'):
                    data=data.replace(f'version = "{installed_version}"'.encode(), f'version = "0.1.0a{sequence}"'.encode())
                if name=='config/managed_asgi.py' and failure=='startup':
                    data=b"raise RuntimeError('Intentional startup failure')\n"+data
                z.writestr('release/'+name,data)
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
            print('PASS: HTTPS download, isolated dependencies, backup, migrations, new server and persistent active release.',flush=True)
            for failure in ['migration','startup']:
                target=archive(2,failure)
                supervisor.apply(job(target,2))
                assert read(supervisor.state/'progress.json')['stage']=='rolled_back', (supervisor.state/'update.log').read_text()[-4000:]
                assert supervisor.active==active
                preserved()
                assert not (supervisor.state/'maintenance').exists()
                print('PASS:',failure,'failure restores previous server, database and files.',flush=True)
    finally:
        supervisor.stop();server.shutdown()
    print('All managed upgrade acceptance checks passed. No real installation data changed.',flush=True)


if __name__=='__main__':main()
