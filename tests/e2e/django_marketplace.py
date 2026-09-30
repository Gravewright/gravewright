"""Real Django marketplace activation, dependency preparation and migration rollback."""
import io
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import zipfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix='gravewright-django-marketplace-') as directory:
        data = Path(directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        from scripts.gravewright_runner import prepare_environment
        prepare_environment(data, port)
        import django
        django.setup()
        from django.conf import settings
        from django.core.management import call_command
        from django.db import connections
        from gravewright.modules.packages import host
        from scripts.update_supervisor import Supervisor, read
        from importlib.metadata import version as installed_version
        call_command('migrate', interactive=False, verbosity=0)

        def package(version, fail=False):
            manifest = {'id': 'test.django', 'name': 'Django integration fixture', 'version': version,
                        'description': 'Activation test', 'author': 'Tests', 'license': 'MIT',
                        'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
                        'django': {'apps': ['marketplace_fixture.apps.FixtureConfig'],
                                   'requirements': ['jsonschema==' + installed_version('jsonschema')]}}
            files = {
                'marketplace_fixture/__init__.py': '',
                'marketplace_fixture/apps.py': 'from django.apps import AppConfig\nclass FixtureConfig(AppConfig):\n name="marketplace_fixture"\n gravewright_urlconf="marketplace_fixture.urls"\n',
                'marketplace_fixture/urls.py': 'from django.http import JsonResponse\nfrom django.urls import path\nurlpatterns=[path("__django_fixture",lambda request: JsonResponse({"version": "' + version + '"}))]\n',
                'marketplace_fixture/migrations/__init__.py': '',
                'marketplace_fixture/migrations/0001_initial.py': 'from django.db import migrations\nclass Migration(migrations.Migration):\n initial=True\n dependencies=[]\n operations=[migrations.RunSQL("CREATE TABLE marketplace_fixture (value TEXT)")]\n',
            }
            if fail:
                files['marketplace_fixture/migrations/0002_fail.py'] = 'from django.db import migrations\ndef fail(apps, schema_editor):\n schema_editor.execute("INSERT INTO marketplace_fixture VALUES (\'broken\')")\n raise RuntimeError("Intentional migration failure")\nclass Migration(migrations.Migration):\n dependencies=[("marketplace_fixture","0001_initial")]\n operations=[migrations.RunPython(fail)]\n'
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, 'w') as archive:
                archive.writestr('manifest.json', json.dumps(manifest))
                for name, content in files.items():
                    archive.writestr(name, content)
            host().install_local(raw.getvalue(), expected_type='module')

        package('1.0.0')
        package('2.0.0', fail=True)
        connections.close_all()
        supervisor = Supervisor(ROOT, data / 'updates', settings.DATABASES['default']['NAME'],
                                settings.MEDIA_ROOT, '127.0.0.1', port)
        try:
            supervisor.start(ROOT)
            supervisor.ready()
            supervisor.apply({'kind': 'django', 'id': 'test.django', 'version': '1.0.0', 'enabled': True})
            progress = read(supervisor.state / 'progress.json')
            assert progress['stage'] == 'complete', (progress, (supervisor.state / 'update.log').read_text())
            with urlopen(f'http://127.0.0.1:{port}/__django_fixture') as response:
                assert json.load(response)['version'] == '1.0.0'
            assert not list(host().directory.rglob('__pycache__'))
            good_python = supervisor.runtime_python
            supervisor.apply({'kind': 'django', 'id': 'test.django', 'version': '2.0.0', 'enabled': True})
            assert read(supervisor.state / 'progress.json')['stage'] == 'rolled_back'
            assert supervisor.runtime_python == good_python
            with urlopen(f'http://127.0.0.1:{port}/__django_fixture') as response:
                assert json.load(response)['version'] == '1.0.0'
            import sqlite3
            with closing(sqlite3.connect(supervisor.database)) as connection:
                assert connection.execute('select count(*) from marketplace_fixture').fetchone()[0] == 0
            supervisor.apply({'kind': 'django', 'id': 'test.django', 'version': '1.0.0', 'enabled': False})
            assert read(supervisor.state / 'progress.json')['stage'] == 'complete'
            assert read(host().directory / 'server-apps.json') == {}
            print('PASS: Django activation, dependency constraints, routes, migrations, rollback and deactivation')
        finally:
            supervisor.stop()
            connections.close_all()
            from scripts.project_files import remove_work_tree
            remove_work_tree(data, Path(tempfile.gettempdir()))


if __name__ == '__main__':
    main()
