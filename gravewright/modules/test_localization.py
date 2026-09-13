import base64
import hashlib
import io
import json
import zipfile

from django.test import TestCase
from gravewright.accounts.models import User, UserPreference
from gravewright.web.localization import LocalizationExtension, tr
from jinja2 import Environment
from . import test_marketplace
from .models import Package
from .packages import host, canonical, ModuleFailure


class LocalizationTests(TestCase):
    setUp = test_marketplace.MarketplaceTests.setUp
    def release(self, catalogs=None, **changes):
        catalogs = catalogs if catalogs is not None else {
            'pt-BR': {'Settings': 'Configurações', 'Campaigns': 'Campanhas', 'Save language': 'Salvar idioma'},
            'es': {'Settings': 'Configuración', 'Campaigns': 'Campañas', 'Save language': 'Guardar idioma'},
        }
        manifest = dict(id='gravewright.translator', name='Translator', version='0.1.0',
                        description='Language options', author='Gravewright', license='MIT',
                        sdk={'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'}, entry='main.js',
                        locales={key: {'name': key, 'path': f'locales/{key}.json'} for key in catalogs})
        manifest.update(changes)
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {start(){},stop(){}}')
            for key, messages in catalogs.items():
                archive.writestr(f'locales/{key}.json', json.dumps(messages))
        raw = output.getvalue()
        record = dict(id=manifest['id'], version=manifest['version'], sdk=manifest['sdk']['requires'],
                      download='https://publisher.example/translator.zip', sha256=hashlib.sha256(raw).hexdigest(), keyId='publisher')
        record['signature'] = base64.b64encode(self.key.sign(canonical(record))).decode()
        return record, raw

    def activate(self, enabled=True):
        return self.client.post('/api/module-packages/activation',
            {'id': 'gravewright.translator', 'version': '0.1.0', 'enabled': enabled}, content_type='application/json')

    def install(self):
        host().install(*self.release())

    def test_global_activation_and_personal_settings(self):
        self.install()
        before = self.client.get('/inside?section=settings')
        self.assertNotContains(before, 'data-language-settings')
        self.assertEqual(self.client.get('/api/module-packages').json()[0]['name'], 'Translator')
        self.assertFalse(self.client.get('/api/module-packages').json()[0]['globalEnabled'])
        response = self.activate()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(self.client.get('/inside?section=settings'), 'data-language-settings')
        response = self.client.post('/inside/language', {'locale': 'pt-BR'})
        self.assertEqual(response.status_code, 302, response.content)
        self.user.name = 'Settings'; self.user.save()
        response = self.client.get('/inside?section=settings')
        self.assertContains(response, '>Configurações</h1>')
        self.assertContains(response, 'value="Settings"')
        self.assertContains(response, 'lang="pt-BR"')
        self.assertEqual(UserPreference.objects.get(user=self.user).locale, 'pt-BR')
        player = User.objects.create_user(email='localization@player.test', name='Settings')
        from django.test import Client
        other = Client(); other.force_login(player)
        self.assertContains(other.get('/inside?section=settings'), '>Settings</h1>')
        self.assertEqual(other.post('/api/module-packages/activation', {'id':'gravewright.translator','version':'0.1.0','enabled':False},content_type='application/json').status_code,403)
        self.assertEqual(self.activate(False).status_code, 200)
        response = self.client.get('/inside?section=settings')
        self.assertNotContains(response, 'data-language-settings')
        self.assertContains(response, '>Settings</h1>')

    def test_invalid_language_returns_controlled_error(self):
        self.install()
        self.assertEqual(self.client.post('/inside/language', {'locale':'pt-BR'}).status_code,400)
        self.activate()
        self.assertEqual(self.client.post('/inside/language', {'locale':'de'}).status_code,400)

    def test_rejects_invalid_catalog_and_placeholders(self):
        for catalogs in [{'en':{'Settings':'X'}}, {'pt-BR': []}, {'pt-BR': {'Hello {name}':'Olá'}}, {'pt-BR':{'Settings':''}}]:
            with self.subTest(catalogs=catalogs), self.assertRaises(ModuleFailure):
                host().install(*self.release(catalogs))
        self.assertFalse(Package.objects.exists())

    def test_revoked_and_tampered_pack_cannot_activate(self):
        self.install()
        package = Package.objects.get()
        package.revoked = True; package.save()
        self.assertEqual(self.activate().status_code,403)
        package.revoked=False; package.save()
        archive = self.directory / 'modules/archives' / (package.digest+'.zip')
        archive.write_bytes(b'changed')
        self.assertEqual(self.activate().status_code,400)

    def test_language_pack_rejected_from_campaign_activation(self):
        self.install()
        from gravewright.campaigns.models import Campaign
        campaign = Campaign.objects.create(owner=self.user, name='Settings')
        with self.assertRaises(ModuleFailure):
            host().configure(campaign.pk, {'gravewright.translator':'0.1.0'}, {}, '0')

    def test_account_without_preference_does_not_inherit_other_account_cookie(self):
        self.install(); self.activate()
        self.client.post('/inside/language', {'locale':'pt-BR'})
        player = User.objects.create_user(email='separate@test.local', name='Player')
        self.client.force_login(player)
        self.assertContains(self.client.get('/inside?section=settings'), '>Settings</h1>')

    def test_static_template_translation_escapes_and_preserves_user_data(self):
        env=Environment(extensions=[LocalizationExtension],autoescape=True)
        env.globals['tr']=tr
        source='<h1>Settings</h1><input value="{{ name }}" title="Settings"><script>const x="Settings";</script><p>{{ name }}</p>'
        template=env.from_string(env.preprocess(source, 'test.html'))
        result=template.render(name='Settings',language={'messages':{'Settings':'<img src=x onerror=alert(1)>'}})
        self.assertIn('&lt;img',result)
        self.assertIn('value="Settings"',result)
        self.assertIn('<p>Settings</p>',result)
        self.assertIn('const x="Settings";',result)
