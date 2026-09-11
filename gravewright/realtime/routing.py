"""Route each table socket to one campaign for the lifetime of the connection."""

from django.urls import path
from .consumers import TableConsumer

websocket_urlpatterns = [path('ws/tables/<uuid:campaign_id>/', TableConsumer.as_asgi())]
