"""Compose HTTP routes from their owning applications.

The top-level Python ``api`` package is an in-process extension interface, not a
Django URL configuration. Browser JSON and file routes remain in app URL modules.
WebSocket routing is configured separately by config.asgi.
"""
from django.contrib import admin
from django.apps import apps
from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path('', include('gravewright.modules.urls')),
    path('', include('gravewright.administration.urls')),
    path('', include('gravewright.actors.urls')),
    path('', include('gravewright.tokens.urls')),
    path('', include('gravewright.journals.urls')),
    path('', include('gravewright.maps.urls')),
    path('admin/', admin.site.urls),
    path('', include('gravewright.table.urls')),
    path('', include('gravewright.web.urls')),
    path('', include('gravewright.campaigns.urls')),
    path('', include('gravewright.accounts.urls')),
]

# A trusted installed app may opt into HTTP routes without editing host URLs.
for app in apps.get_app_configs():
    if (app.name in settings.GRAVEWRIGHT_SERVER_APPS or
            f'{type(app).__module__}.{type(app).__name__}' in settings.GRAVEWRIGHT_SERVER_APPS):
        urlconf = getattr(app, 'gravewright_urlconf', None)
        if urlconf:
            urlpatterns += [path('', include(urlconf))]
