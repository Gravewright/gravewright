"""Interpret proxy scheme headers only from explicitly trusted network peers.

Keep the ASGI server's proxy-header rewriting disabled: ``scope['client']`` must
identify the actual connecting proxy, not an address supplied in an HTTP header.
"""

from ipaddress import ip_address, ip_network

from django.conf import settings


class TrustedProxySchemeMiddleware:
    """Normalize HTTP/WebSocket schemes before Django and origin validation.

    A single X-Forwarded-Proto value from TRUSTED_PROXIES describes the external
    transport. Untrusted or ambiguous headers leave the transport scope alone;
    forwarded host and client-address headers do not establish this trust.
    """

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        peer = scope.get('client')
        if scope['type'] in {'http', 'websocket'} and peer:
            try:
                address = ip_address(peer[0])
            except ValueError:
                address = None
            if address is not None and any(
                address in ip_network(network, strict=False)
                for network in settings.TRUSTED_PROXIES
            ):
                values = [value for name, value in scope.get('headers', [])
                          if name.lower() == b'x-forwarded-proto']
                if not values and getattr(settings, 'GRAVEWRIGHT_ALLOW_TUNNELS', False):
                    # Some tunnel agents omit scheme headers. A browser Origin
                    # may establish HTTPS only when it matches this exact Host.
                    from gravewright.realtime.security import origin_tuple
                    hosts = [value for name, value in scope.get('headers', []) if name.lower() == b'host']
                    origins = [value for name, value in scope.get('headers', []) if name.lower() == b'origin']
                    if len(hosts) == len(origins) == 1:
                        try:
                            origin = origin_tuple(origins[0].decode('ascii'))
                            if origin == origin_tuple(origin[0] + '://' + hosts[0].decode('ascii')):
                                values = [origin[0].encode('ascii')]
                        except (ValueError, UnicodeError):
                            pass
                # Multiple headers and comma-separated chains are ambiguous.
                if len(values) == 1 and values[0] in {b'http', b'https'}:
                    scheme = values[0].decode('ascii')
                    if scope['type'] == 'websocket':
                        scheme = 'wss' if scheme == 'https' else 'ws'
                    scope = {**scope, 'scheme': scheme}
        await self.application(scope, receive, send)
