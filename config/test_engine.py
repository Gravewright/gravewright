import os
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory, override_settings
from config.engine import configure
from config.size_limits import SIZE_DEFAULTS, size_bytes
from gravewright.accounts.client_ip import client_ip


class EngineConfigurationTests(SimpleTestCase):
    def test_invalid_limits_fail_at_startup(self):
        for name in ('WS_MAX_MESSAGE_BYTES', 'JOURNAL_IMAGE_MAX_BYTES', 'MAP_MAX_TILE_COUNT', 'CAMPAIGN_SNAPSHOT_RETENTION'):
            with self.subTest(name=name), patch.dict(os.environ, {name: '0'}):
                os.environ.pop(name.removesuffix('_BYTES') + '_MB', None)
                with self.assertRaises(ValueError):
                    configure()

    def test_size_limits_convert_mb_and_support_legacy_bytes(self):
        for name, default in SIZE_DEFAULTS.items():
            key = name.removesuffix('_BYTES') + '_MB'
            with self.subTest(name=name):
                self.assertEqual(size_bytes({}, name, default), default)
                self.assertEqual(size_bytes({name: '12345'}, name, default), 12345)
                self.assertEqual(size_bytes({key: '1.5', name: '999'}, name, default), 1572864)
                for value in ('0', '-1', 'nan', 'Infinity', 'invalid', '0.00000001'):
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        size_bytes({key: value}, name, default)
        with patch.dict(os.environ, {'MAP_UPLOAD_MAX_MB': '2.5'}):
            self.assertEqual(configure()['MAP_UPLOAD_MAX_BYTES'], 2621440)

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
