import json
from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.test import TransactionTestCase
from . import test_marketplace
from .models import Package
from .packages import ModuleFailure

class InstallProgressTests(TransactionTestCase):
    setUp = test_marketplace.MarketplaceTests.setUp
    release = test_marketplace.MarketplaceTests.release

    def collect(self):
        response = self.client.post('/api/marketplace/install', {'id':'publisher.test','version':'1.0.0'}, content_type='application/json', HTTP_ACCEPT='application/x-ndjson')
        self.assertEqual(response.status_code, 200)
        async def consume():
            return [json.loads(chunk) async for chunk in response.streaming_content]
        return async_to_sync(consume)()

    def test_reports_download_bytes_and_completes_after_install(self):
        record, raw = self.release(tags=['Tradução', 'Accessibility'])
        def download(url, limit, progress=None):
            if progress:
                progress(len(raw)//2, len(raw)); progress(len(raw), len(raw))
            return raw
        with patch('gravewright.modules.views.catalog', return_value=[record]), patch('gravewright.modules.views.download', side_effect=download):
            events = self.collect()
        self.assertEqual([e['stage'] for e in events], ['catalog','download','download','download','verify','complete'])
        self.assertEqual(events[2]['received'],len(raw)//2)
        self.assertTrue(Package.objects.filter(module_id='publisher.test').exists())
        self.assertEqual(self.client.get('/api/module-packages').json()[0]['tags'], ['Tradução','Accessibility'])

    def test_failed_download_does_not_report_success_or_install(self):
        record, _ = self.release()
        with patch('gravewright.modules.views.catalog', return_value=[record]), patch('gravewright.modules.views.download', side_effect=ModuleFailure('unavailable')):
            events = self.collect()
        self.assertEqual(events[-1], {'stage':'error','error':'unavailable'})
        self.assertNotIn('complete', [e['stage'] for e in events])
        self.assertFalse(Package.objects.exists())
