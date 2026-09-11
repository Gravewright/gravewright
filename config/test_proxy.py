"""Proxy trust and its effect on Django HTTPS security processing."""

import json

from channels.testing import HttpCommunicator
from django.core.asgi import get_asgi_application
from django.test import SimpleTestCase, override_settings

from config.proxy import TrustedProxySchemeMiddleware


@override_settings(TRUSTED_PROXIES=('10.0.0.0/8', '::1/128'))
class ProxySchemeTests(SimpleTestCase):
    async def observed_scope(self, original):
        observed = []

        async def capture(scope, receive, send):
            observed.append(scope)

        await TrustedProxySchemeMiddleware(capture)(original, None, None)
        return observed[0]

    async def test_trusted_ipv4_and_ipv6_peers_normalize_both_protocols(self):
        for peer in ('10.2.3.4', '::1'):
            for kind, forwarded, expected in (
                ('http', b'https', 'https'), ('http', b'http', 'http'),
                ('websocket', b'https', 'wss'), ('websocket', b'http', 'ws'),
            ):
                with self.subTest(peer=peer, kind=kind, forwarded=forwarded):
                    original = {'type': kind, 'client': (peer, 1234),
                                'headers': [(b'x-forwarded-proto', forwarded)]}
                    result = await self.observed_scope(original)
                    self.assertEqual(result['scheme'], expected)
                    self.assertNotIn('scheme', original)
                    self.assertIsNot(result, original)

    async def test_untrusted_missing_or_invalid_peer_cannot_forward_scheme(self):
        for peer in (None, ('192.0.2.1', 1234), ('invalid', 1234)):
            original = {'type': 'http', 'scheme': 'http', 'client': peer,
                        'headers': [(b'x-forwarded-proto', b'https'),
                                    (b'x-forwarded-for', b'10.1.2.3')]}
            self.assertIs(await self.observed_scope(original), original)

    async def test_ambiguous_or_unsupported_header_does_not_override_transport(self):
        for values in ([], [b''], [b'HTTPS'], [b' https '], [b'ftp'],
                       [b'https,http'], [b'https, https'], [b'https', b'https']):
            with self.subTest(values=values):
                original = {'type': 'websocket', 'scheme': 'ws', 'client': ('10.1.2.3', 1234),
                            'headers': [(b'x-forwarded-proto', value) for value in values]}
                self.assertIs(await self.observed_scope(original), original)

    async def test_other_protocols_are_untouched(self):
        original = {'type': 'lifespan', 'client': ('10.1.2.3', 1234),
                    'headers': [(b'x-forwarded-proto', b'https')]}
        self.assertIs(await self.observed_scope(original), original)


@override_settings(ALLOWED_HOSTS=['testserver'], TRUSTED_PROXIES=('10.0.0.0/8',),
                   SECURE_HSTS_SECONDS=31536000, CSRF_COOKIE_SECURE=True,
                   CSRF_COOKIE_NAME='__Host-gravewright-csrf',
                   GRAVEWRIGHT_PUBLIC_ORIGIN='https://testserver',
                   CSRF_TRUSTED_ORIGINS=['https://testserver'])
class ProxyDjangoSecurityTests(SimpleTestCase):
    async def request(self, *, peer='10.1.2.3', method='GET', path='/api/security/csrf',
                      headers=(), body=b''):
        # SecurityMiddleware captures settings at construction. Build the HTTP
        # stack inside this test's overrides, as a configured process would.
        application = TrustedProxySchemeMiddleware(get_asgi_application())
        client = HttpCommunicator(application, method, path, body=body, headers=[
            (b'host', b'testserver'), (b'x-forwarded-proto', b'https'), *headers,
        ])
        client.scope.update(scheme='http', client=(peer, 1234))
        response = await client.get_response(timeout=5)
        await client.wait(timeout=5)
        return response

    async def test_only_trusted_proxy_makes_django_emit_hsts(self):
        trusted = await self.request()
        self.assertEqual(trusted['status'], 200)
        headers = {name.lower(): value for name, value in trusted['headers']}
        self.assertEqual(headers[b'strict-transport-security'], b'max-age=31536000')
        untrusted = await self.request(peer='192.0.2.1')
        self.assertEqual(untrusted['status'], 200)
        self.assertNotIn(b'strict-transport-security',
                         {name.lower(): value for name, value in untrusted['headers']})

    async def test_forwarded_https_applies_csrf_referer_validation(self):
        initial = await self.request()
        token = json.loads(initial['body'])['token']
        cookie = next(value.split(b';', 1)[0] for name, value in initial['headers']
                      if name.lower() == b'set-cookie')
        # A safe GET-only route returns 405 after successful CSRF processing.
        # This exercises Security/CSRF without account writes or database access.
        auth = [(b'cookie', cookie), (b'x-csrf-token', token.encode())]
        for referer in (None, b'https://evil.example/', b'http://testserver/'):
            extra = [] if referer is None else [(b'referer', referer)]
            result = await self.request(method='POST', headers=[*auth, *extra])
            self.assertEqual(result['status'], 403)
        for header in ((b'referer', b'https://testserver/inside'),
                       (b'origin', b'https://testserver')):
            result = await self.request(method='POST', headers=[*auth, header])
            self.assertEqual(result['status'], 405)
