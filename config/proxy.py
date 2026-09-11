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
                # Multiple headers and comma-separated chains are ambiguous.
                if len(values) == 1 and values[0] in {b'http', b'https'}:
                    scheme = values[0].decode('ascii')
                    if scope['type'] == 'websocket':
                        scheme = 'wss' if scheme == 'https' else 'ws'
                    scope = {**scope, 'scheme': scheme}
        await self.application(scope, receive, send)
