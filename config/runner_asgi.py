"""Local desktop transport guard; this module is not a public server entry point."""

from config.asgi import application as project_application
from django.conf import settings


class LocalOnlyMiddleware:
    """Reject non-loopback peers even if someone overrides Daphne's bind address.

    The Runner binds IPv4 loopback and does not trust forwarding headers. Host,
    CSRF, session and WebSocket origin checks still run in the normal stack.
    """

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        peer = scope.get('client')
        hosts = [value for name, value in scope.get('headers', []) if name.lower() == b'host']
        allowed = {f'127.0.0.1:{settings.GRAVEWRIGHT_PORT}'.encode('ascii')}
        if settings.GRAVEWRIGHT_PORT == 80:
            allowed.add(b'127.0.0.1')
        local = bool(peer and peer[0] == '127.0.0.1')
        valid_host = len(hosts) == 1 and hosts[0] in allowed
        if scope['type'] in {'http', 'websocket'} and (not local or not valid_host):
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 4403})
            else:
                await send({'type': 'http.response.start', 'status': 400 if local else 403,
                            'headers': [(b'content-type', b'text/plain'),
                                        (b'cache-control', b'no-store')]})
                await send({'type': 'http.response.body', 'body': b'Local access only.'})
            return
        await self.application(scope, receive, send)


application = LocalOnlyMiddleware(project_application)
