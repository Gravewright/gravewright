import os
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory, override_settings
from config.engine import configure
from gravewright.accounts.client_ip import client_ip


class EngineConfigurationTests(SimpleTestCase):
    def test_invalid_limits_fail_at_startup(self):
        for name in ('WS_MAX_MESSAGE_BYTES', 'JOURNAL_IMAGE_MAX_BYTES', 'MAP_MAX_TILE_COUNT', 'CAMPAIGN_SNAPSHOT_RETENTION'):
            with self.subTest(name=name), patch.dict(os.environ, {name: '0'}):
                with self.assertRaises(ValueError):
                    configure()

    def test_invalid_expiration_and_viewport(self):
        for values in ({'JOIN_CODE_DEFAULT_EXPIRES_HOURS':'9999'}, {'SCENE_VIEWPORT_MAX_AREA_CHUNKS':'9999'}):
            with patch.dict(os.environ, values):
                with self.assertRaises(ValueError):
                    configure()

    @override_settings(TRUSTED_PROXIES=('10.0.0.0/8',))
    def test_only_trusted_proxy_can_forward_client_ip(self):
        factory = RequestFactory()
        for peer, forwarded, expected in (
            ('192.0.2.1', '198.51.100.1', '192.0.2.1'),
            ('10.0.0.1', '198.51.100.1, 10.0.0.2', '198.51.100.1'),
            ('10.0.0.1', 'forged, 192.0.2.1', '192.0.2.1'),
            ('10.0.0.1', 'invalid', '10.0.0.1'),
        ):
            with self.subTest(peer=peer, forwarded=forwarded):
                request = factory.get('/', REMOTE_ADDR=peer, HTTP_X_FORWARDED_FOR=forwarded)
                self.assertEqual(client_ip(request), expected)
