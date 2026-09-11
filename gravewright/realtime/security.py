"""Reject WebSocket handshakes whose browser origin does not match the request host."""

from urllib.parse import urlsplit

from django.conf import settings
from django.http.request import split_domain_port, validate_host


def origin_tuple(value):
    """Parse an HTTP origin without accepting URL credentials or hidden delimiters."""
    # urlsplit strips some control characters; reject them before parsing.
    if (not value or any(char.isspace() or ord(char) < 32 or ord(char) == 127
                         for char in value) or '?' in value or '#' in value):
        raise ValueError('Invalid origin.')
    origin = urlsplit(value)
    if (origin.scheme not in {'http', 'https'} or not origin.hostname
            or origin.username is not None or origin.password is not None
            or origin.path not in ('', '/') or origin.netloc.endswith(':')):
        raise ValueError('Invalid origin.')
    port = origin.port
    if port is None:
        port = 443 if origin.scheme == 'https' else 80
    if port == 0:
        raise ValueError('Invalid origin port.')
    return origin.scheme, origin.hostname, port


class SameOriginWebSocketMiddleware:
    """Require the configured public origin, or the local transport origin.

    A public origin is an operator-defined browser origin policy, not evidence
    that the upstream socket uses TLS. It also works when Daphne omits scheme
    or a TLS proxy connects over plain HTTP. Host and effective port must still
    match, and the host must be allowed. Headers cannot override this policy.
    """
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        headers = scope.get('headers', [])
        hosts = [v.decode('latin1') for k, v in headers if k.lower() == b'host']
        origins = [v.decode('latin1') for k, v in headers if k.lower() == b'origin']
        valid = False
        if len(hosts) == len(origins) == 1:
            try:
                public_origin = settings.GRAVEWRIGHT_PUBLIC_ORIGIN
                if public_origin:
                    expected = origin_tuple(public_origin)
                    scheme = expected[0]
                else:
                    scheme = {'ws': 'http', 'wss': 'https'}[scope.get('scheme', 'ws')]
                    expected = origin_tuple(scheme + '://' + hosts[0])
                domain, _ = split_domain_port(hosts[0].lower())
                valid = (bool(domain) and validate_host(domain, settings.ALLOWED_HOSTS)
                         and origin_tuple(scheme + '://' + hosts[0]) == expected
                         and origin_tuple(origins[0]) == expected)
            except (KeyError, ValueError):
                pass
        if not valid:
            await send({'type': 'websocket.close', 'code': 4403})
            return
        await self.application(scope, receive, send)
