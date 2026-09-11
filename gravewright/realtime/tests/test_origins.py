"""Origin authorization at the ASGI boundary, including TLS proxy deployments."""

from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from config.proxy import TrustedProxySchemeMiddleware
from gravewright.realtime.security import SameOriginWebSocketMiddleware


async def accept_socket(scope, receive, send):
    await receive()
    await send({'type': 'websocket.accept'})


@override_settings(ALLOWED_HOSTS=['vtt.example', '[::1]'],
                   GRAVEWRIGHT_PUBLIC_ORIGIN='https://vtt.example',
                   TRUSTED_PROXIES=())
class OriginTests(SimpleTestCase):
    async def check(self, origin=b'https://vtt.example', host=b'vtt.example',
                    *, accepted=True, headers=(), scope=None):
        request_headers = list(headers)
        if origin is not None:
            request_headers.append((b'origin', origin))
        if host is not None:
            request_headers.append((b'host', host))
        application = TrustedProxySchemeMiddleware(SameOriginWebSocketMiddleware(accept_socket))
        socket = WebsocketCommunicator(application, '/ws/', headers=request_headers)
        socket.scope.update(scope or {})
        connected, detail = await socket.connect()
        self.assertEqual(connected, accepted)
        if not accepted:
            self.assertEqual(detail, 4403)
        await socket.wait()

    async def test_public_https_origin_works_with_missing_or_upstream_ws_scheme(self):
        for scope in ({}, {'scheme': 'ws'}, {'scheme': 'wss'}):
            with self.subTest(scope=scope):
                await self.check(scope=scope)

    async def test_default_ports_and_hostname_case_are_equivalent(self):
        await self.check(origin=b'https://VTT.EXAMPLE:443', host=b'VTT.EXAMPLE')
        await self.check(host=b'vtt.example:443')
        await self.check(origin=b'https://vtt.example/')

    @override_settings(GRAVEWRIGHT_PUBLIC_ORIGIN='https://vtt.example:8443')
    async def test_public_port_must_match_both_origin_and_host(self):
        await self.check(origin=b'https://vtt.example:8443', host=b'vtt.example:8443')
        await self.check(origin=b'https://vtt.example:8443', accepted=False)
        await self.check(host=b'vtt.example:8443', accepted=False)
        await self.check(accepted=False)

    @override_settings(GRAVEWRIGHT_PUBLIC_ORIGIN='https://[::1]:8443')
    async def test_ipv6_origin_and_host_keep_the_public_port(self):
        await self.check(origin=b'https://[::1]:8443', host=b'[::1]:8443')
        await self.check(origin=b'https://[::1]', host=b'[::1]:8443', accepted=False)

    @override_settings(ALLOWED_HOSTS=['other.example'])
    async def test_public_origin_does_not_bypass_allowed_hosts(self):
        await self.check(accepted=False)

    @override_settings(ALLOWED_HOSTS=['vtt.example', 'other.example'])
    async def test_other_allowed_hosts_and_origins_cannot_replace_public_origin(self):
        await self.check(origin=b'https://other.example', accepted=False)
        await self.check(host=b'other.example', accepted=False)
        await self.check(origin=b'https://other.example', host=b'other.example', accepted=False)
        await self.check(origin=b'http://vtt.example', accepted=False)

    async def test_missing_duplicate_and_malformed_headers_fail_closed(self):
        for origin in (None, b'null', b'', b'https://@vtt.example',
                       b'https://user:password@vtt.example', b'https://vtt.example:0',
                       b'https://vtt.example:65536', b'https://vtt.example:',
                       b'https://vtt.example/path', b'https://vtt.example?',
                       b'https://vtt.example#', b'https://vtt.example\t',
                       b'\x00https://vtt.example', b'https://vtt.example,https://evil.example'):
            with self.subTest(origin=origin):
                await self.check(origin=origin, accepted=False)
        for host in (None, b'', b'vtt.example:0', b'vtt.example:',
                     b'@vtt.example', b'vtt.example/', b'vtt.example\n'):
            with self.subTest(host=host):
                await self.check(host=host, accepted=False)
        for header in ((b'origin', b'https://vtt.example'), (b'host', b'vtt.example')):
            await self.check(headers=[header], accepted=False)

    @override_settings(TRUSTED_PROXIES=('127.0.0.1/32',))
    async def test_forwarding_headers_cannot_change_configured_origin(self):
        await self.check(scope={'client': ('127.0.0.1', 1234)},
                         headers=[(b'x-forwarded-proto', b'http')])
        await self.check(origin=b'http://vtt.example', accepted=False,
                         scope={'client': ('127.0.0.1', 1234)},
                         headers=[(b'x-forwarded-proto', b'http')])
        await self.check(origin=b'https://evil.example', accepted=False,
                         headers=[(b'x-forwarded-host', b'evil.example'),
                                  (b'forwarded', b'host=evil.example;proto=https')])

    @override_settings(GRAVEWRIGHT_PUBLIC_ORIGIN='')
    async def test_unconfigured_origin_uses_only_the_transport_scheme(self):
        await self.check(origin=b'http://vtt.example')
        await self.check(accepted=False)
        await self.check(scope={'scheme': 'wss'})
        await self.check(origin=b'http://vtt.example', scope={'scheme': 'ws'})
        for scheme in ('https', 'ftp', '', None):
            with self.subTest(scheme=scheme):
                await self.check(scope={'scheme': scheme}, accepted=False)
        await self.check(accepted=False, scope={'client': ('192.0.2.1', 1234)},
                         headers=[(b'x-forwarded-proto', b'https')])

    @override_settings(GRAVEWRIGHT_PUBLIC_ORIGIN='', TRUSTED_PROXIES=('127.0.0.1/32',))
    async def test_trusted_proxy_supplies_scheme_for_local_origin_fallback(self):
        await self.check(scope={'client': ('127.0.0.1', 1234)},
                         headers=[(b'x-forwarded-proto', b'https')])
