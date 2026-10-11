"""Disposable table fixtures for complete system sheet implementations."""
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
fixture = ROOT / 'data' / 'system-sheets-review' / secrets.token_hex(8)
fixture.mkdir(parents=True)
settings.DATABASES['default']['NAME'] = fixture / 'review.sqlite3'
settings.MEDIA_ROOT = fixture / 'media'
settings.GRAVEWRIGHT_MODULES_ROOT = fixture / 'modules'
settings.GRAVEWRIGHT_SERVER_APPS_REGISTRY = fixture / 'server-apps.json'
settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
settings.DEBUG = True
settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
from django.core.management import call_command
call_command('migrate', verbosity=0, interactive=False)
from django.test import Client
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.actors.models import Actor
from gravewright.maps.models import Scene, Broadcast
from gravewright.modules.models import Package, ModuleSet
from gravewright.pdf_system.schema import normalize
from gravewright.tokens.models import Token
gm = User.objects.create_user('sheets@example.test', secrets.token_urlsafe(20), name='GM', role='owner')
client = Client(); client.force_login(gm)
manifest = {
    'id': 'review.rules', 'name': 'Review Rules', 'version': '1.0.0',
    'description': 'Complete sheet fixture', 'author': 'Review', 'license': 'MIT',
    'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'}, 'entry': 'main.js',
    'system': {'actorTypes': [{'id': 'hero', 'label': 'Hero'}]},
}
Package.objects.create(module_id=manifest['id'], version='1.0.0', digest='a' * 64, manifest=manifest, record={})
seed = {'session': {'name': settings.SESSION_COOKIE_NAME, 'value': client.cookies[settings.SESSION_COOKIE_NAME].value}}
for key, system in [('pdf', 'gravewright-pdf-system'), ('custom', manifest['id'])]:
    campaign = Campaign.objects.create(owner=gm, name=key + ' sheet review', system=system)
    Membership.objects.create(campaign=campaign, user=gm, role='gm')
    actor = Actor.objects.create(campaign=campaign, name=key + ' hero', type='hero' if key == 'custom' else 'character', data={'health': 12} if key == 'custom' else normalize({}))
    scene = Scene.objects.create(campaign=campaign, name='Review scene', width=800, height=600)
    Broadcast.objects.create(campaign=campaign, scene=scene)
    token = Token.objects.create(scene=scene, actor=actor)
    if key == 'custom':
        ModuleSet.objects.create(campaign=campaign, modules={manifest['id']: '1.0.0'})
    seed[key] = dict(campaign=str(campaign.pk), actor=str(actor.pk), token=str(token.pk), scene=str(scene.pk))
(ROOT / 'data' / 'system-sheets-seed.json').write_text(json.dumps(seed), encoding='utf-8')
print('System sheets review ready on port 30003', flush=True)
call_command('runserver', '127.0.0.1:30003', use_reloader=False, verbosity=0)
