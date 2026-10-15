"""Serve disposable compendium fixtures, optionally using local system ZIPs.

python tests/e2e/compendium_server.py --fixture data/compendium-review/new
python tests/e2e/compendium_layout.py --seed data/compendium-review/new/seed.json

Repeat --archive to review real browser systems. The default system and every
editable pack are synthetic. No .env, operator database or content is imported.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import secrets
import socket
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--archive', type=Path, action='append', default=[])
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    fixture = args.fixture.resolve()
    if fixture.exists() and any(fixture.iterdir()):
        raise RuntimeError('Use a new, empty fixture directory.')
    fixture.mkdir(parents=True, exist_ok=True)
    from scripts.runtime_storage import configure_runtime_storage
    configure_runtime_storage(ROOT, 'data/runner/compendium-review')
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', args.port))
        port = connection.getsockname()[1]
    os.environ.update({
        'PYTHON_DOTENV_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'DJANGO_SETTINGS_MODULE': 'config.settings', 'DJANGO_DEBUG': 'true',
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64), 'DEFAULT_LOCALE': 'en',
        'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost,testserver', 'DJANGO_SECURE_COOKIES': 'false',
        'GRAVEWRIGHT_DATABASE': str(fixture / 'review.sqlite3'),
        'GRAVEWRIGHT_MEDIA_ROOT': str(fixture / 'media'),
        'GRAVEWRIGHT_MODULES_ROOT': str(fixture / 'modules'),
        'GRAVEWRIGHT_CONTENT_ROOT': str(fixture / 'content'),
        'GRAVEWRIGHT_SERVER_APPS': '', 'GRAVEWRIGHT_SERVER_APP_PATHS': '',
        'GRAVEWRIGHT_API_MODULES_ROOT': '', 'GRAVEWRIGHT_DJANGO_MODULES_ROOT': '',
        'GRAVEWRIGHT_DJANGO_REGISTRY': str(fixture / 'modules/server-apps.json'),
        'GRAVEWRIGHT_REDIS_URL': '', 'GRAVEWRIGHT_MARKETPLACE_URL': '',
        'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': '', 'GRAVEWRIGHT_RELEASES_REPOSITORY': '',
        'GRAVEWRIGHT_HOST': '127.0.0.1', 'GRAVEWRIGHT_PORT': str(port),
        'GRAVEWRIGHT_PUBLIC_ORIGIN': '', 'TRUSTED_PROXIES': '',
    })
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.test import Client
    from django.utils import timezone
    from gravewright.accounts.models import User
    from gravewright.campaigns.models import Campaign, Membership, Onboarding
    from gravewright.compendiums.models import Entry, Pack
    from gravewright.maps.models import Broadcast, Scene
    from gravewright.maps.services import DEFAULTS
    from gravewright.modules.models import ModuleSet
    from gravewright.modules.packages import host

    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    call_command('migrate', verbosity=0, interactive=False)
    users = {name: User.objects.create_user(f'{name}@compendium-review.test', secrets.token_urlsafe(20),
             name=name.title(), role='owner' if name == 'gm' else 'participant')
             for name in ('gm', 'reader')}
    sessions = {}
    for name, user in users.items():
        client = Client(); client.force_login(user)
        sessions[name] = {'name': settings.SESSION_COOKIE_NAME,
                          'value': client.cookies[settings.SESSION_COOKIE_NAME].value}
    # A synthetic declarative language module exercises the real locale endpoint.
    translations = {
        'pt-BR': {'Compendiums':'Compêndios','Create compendium':'Criar compêndio','Search compendiums':'Pesquisar compêndios',
                  'Content type':'Tipo de conteúdo','Compendium':'Compêndio','All types':'Todos os tipos',
                  'All compendiums':'Todos os compêndios','Characters':'Personagens','Items':'Itens','Journals':'Diários',
                  'Scenes':'Cenas','Decks':'Baralhos','Permissions':'Permissões','Import':'Importar','Preview':'Prévia',
                  'Close':'Fechar','No matching content.':'Nenhum conteúdo encontrado.','No description.':'Sem descrição.',
                  'Empty package.':'Pacote vazio.','Name':'Nome','Loading…':'Carregando…','Cancel':'Cancelar'},
        'es': {'Compendiums':'Compendios','Create compendium':'Crear compendio','Search compendiums':'Buscar compendios',
               'Content type':'Tipo de contenido','Compendium':'Compendio','All types':'Todos los tipos',
               'All compendiums':'Todos los compendios','Characters':'Personajes','Items':'Objetos','Journals':'Diarios',
               'Scenes':'Escenas','Decks':'Barajas','Permissions':'Permisos','Import':'Importar','Preview':'Vista previa',
               'Close':'Cerrar','No matching content.':'Ningún contenido encontrado.','No description.':'Sin descripción.',
               'Empty package.':'Paquete vacío.','Name':'Nombre','Loading…':'Cargando…','Cancel':'Cancelar'},
    }
    language_manifest = {'id':'example.compendium-languages','version':'0.1.0','name':'Synthetic review languages',
                        'description':'Disposable browser review','author':'Gravewright tests','license':'MIT',
                        'entry':'main.js','sdk':{'requires':'>=1.0.0 <2.0.0','tested':'1.0.0'},
                        'locales':{locale:{'name':locale,'path':f'locales/{locale}.json'} for locale in translations}}
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as archive:
        archive.writestr('manifest.json', json.dumps(language_manifest))
        archive.writestr('main.js', 'export default {start(){},stop(){}};')
        for locale, messages in translations.items():
            archive.writestr(f'locales/{locale}.json', json.dumps(messages, ensure_ascii=False))
    host().install_local(buffer.getvalue(), expected_type='module')
    client = Client(); client.force_login(users['gm'])
    response = client.post('/api/module-packages/activation', {'id':language_manifest['id'],'version':'0.1.0','enabled':True}, content_type='application/json')
    if response.status_code != 200:
        raise RuntimeError(f'Could not activate synthetic review languages: {response.content!r}')
    archives = [path.resolve().read_bytes() for path in args.archive]
    if not archives:
        manifest = {'id': 'example.compendium-review', 'version': '0.1.0', 'name': 'Synthetic compendium review',
                    'description': 'Disposable browser review', 'author': 'Gravewright tests', 'license': 'MIT',
                    'entry': 'main.js', 'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
                    'system': {'actorTypes': [{'id': 'character', 'label': 'Character'}],
                               'itemTypes': [{'id': 'gear', 'label': 'Gear'}]}}
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {start(){},stop(){}};')
        archives.append(buffer.getvalue())
    systems = {}
    for archive in archives:
        package = host().install_local(archive, expected_type='system')
        with ZipFile(io.BytesIO(archive)) as source:
            manifest = json.loads(source.read('manifest.json'))
        campaign = Campaign.objects.create(owner=users['gm'], name='Compendium review ' + package['id'], system=package['id'])
        for name, user in users.items():
            membership = Membership.objects.create(campaign=campaign, user=user, role='gm' if name == 'gm' else 'player')
            Onboarding.objects.create(membership=membership, dismissed=True, player_shown_at=timezone.now())
        ModuleSet.objects.create(campaign=campaign, modules={package['id']: package['version']})
        scene = Scene.objects.create(campaign=campaign, name='Review scene', width=1024, height=768, settings=deepcopy(DEFAULTS))
        Broadcast.objects.create(campaign=campaign, scene=scene)
        types = [(kind, row['id']) for kind, key in [('actor', 'actorTypes'), ('item', 'itemTypes')]
                 for row in manifest['system'].get(key, [])]
        if not any(kind == 'item' for kind, _ in types) or not any(kind == 'actor' for kind, _ in types):
            raise RuntimeError('The compendium review requires at least one actor and one item type.')
        packs = []
        for name in ('Zeta review', 'Álgebra review', 'Alfa review', 'Beta review'):
            pack = Pack.objects.create(campaign=campaign, name=name, system_id=package['id'], shared=name != 'Beta review')
            entries = []
            samples = [('Zebra 10', 'item', types[-1][1], 'Synthetic long description. ' * 1200),
                       ('Árvore 2', 'item', types[-1][1], 'Synthetic short description.'),
                       ('Arvore 10', 'item', types[-1][1], 'Synthetic short description.'),
                       ('Alfa hero', 'actor', types[0][1], 'Synthetic compendium description.\nSecond paragraph: ação, élan.'),
                       ('Long empty ' + 'review name ' * 8, 'item', types[-1][1], ''),
                       ('Álgebra notes', 'journal', 'text', 'Synthetic journal description.')]
            if name == 'Zeta review':
                samples += [(f'Synthetic {kind} {typ}', kind, typ, 'Synthetic type description.') for kind, typ in types]
            for entry_name, kind, typ, description in samples:
                data = {'name': entry_name, 'type': typ, 'data': {'description': description, 'review': {'copy': 'original'}}}
                if kind == 'journal': data = {'title': entry_name, 'type': typ, 'data': {'content': description}}
                entry = Entry.objects.create(pack=pack, name=entry_name, kind=kind, data=data)
                entries.append({'id': str(entry.pk), 'name': entry_name, 'kind': kind, 'type': typ})
            packs.append({'id': str(pack.pk), 'name': name, 'entries': entries})
        systems[package['id']] = {'campaign': str(campaign.pk), 'scene': str(scene.pk), 'sessions': sessions,
                                  'users': {name: str(user.pk) for name, user in users.items()}, 'packs': packs}
    empty = Campaign.objects.create(owner=users['gm'], name='Empty compendium review', system='')
    for name, user in users.items():
        membership = Membership.objects.create(campaign=empty, user=user, role='gm' if name == 'gm' else 'player')
        Onboarding.objects.create(membership=membership, dismissed=True, player_shown_at=timezone.now())
    seed = {'kind': 'compendium-layout-review', 'fixture': str(fixture), 'base': f'http://127.0.0.1:{port}',
            'systems': systems, 'emptyCampaign':str(empty.pk), 'sessions':sessions}
    (fixture / 'seed.json').write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'seed': str(fixture / 'seed.json'), 'base': seed['base']}), flush=True)
    call_command('runserver', f'127.0.0.1:{port}', use_reloader=False, verbosity=0)


if __name__ == '__main__':
    main()
