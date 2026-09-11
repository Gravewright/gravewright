"""ASGI entry point for HTTP and authenticated campaign WebSockets.

Django is initialized before importing consumers because their service imports
access registered models. Trusted proxy scheme handling precedes Django HTTP
security and WebSocket origin checks; socket session auth follows origin checks.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from gravewright.realtime.routing import websocket_urlpatterns
from gravewright.realtime.security import SameOriginWebSocketMiddleware
from config.proxy import TrustedProxySchemeMiddleware

application = TrustedProxySchemeMiddleware(ProtocolTypeRouter({
    'http': django_application,
    'websocket': SameOriginWebSocketMiddleware(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
}))
