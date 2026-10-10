"""Single-process desktop profile with optional local HTTPS tunnel support.

The launcher supplies isolated environment values and holds the data-directory
lock. The server binds loopback; an explicitly configured local tunnel agent
may forward the public HTTPS origin. Direct hosting uses config.settings.
"""

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


_data = os.environ.get('GRAVEWRIGHT_RUNNER_DATA', '')
GRAVEWRIGHT_ALLOW_TUNNELS = os.environ.get('GRAVEWRIGHT_ALLOW_TUNNELS') == 'true'
_origin = f'http://127.0.0.1:{GRAVEWRIGHT_PORT}'
if (not _data or not Path(_data).is_absolute() or DEBUG
        or GRAVEWRIGHT_HOST != '127.0.0.1'
        or GRAVEWRIGHT_REDIS_URL):
    raise ImproperlyConfigured('Start the local profile with Gravewright Runner.')
if GRAVEWRIGHT_ALLOW_TUNNELS:
    if (GRAVEWRIGHT_PUBLIC_ORIGIN or ALLOWED_HOSTS != ['*']
            or set(TRUSTED_PROXIES) != {'127.0.0.1/32', '::1/128'}):
        raise ImproperlyConfigured('Start the tunnel profile with Gravewright Runner.')
elif (GRAVEWRIGHT_PUBLIC_ORIGIN != _origin or ALLOWED_HOSTS != ['127.0.0.1']
      or TRUSTED_PROXIES or SESSION_COOKIE_SECURE):
    raise ImproperlyConfigured('Start the local profile with Gravewright Runner.')

RUNNER_DATA = Path(_data).resolve()
RUNNER_TOKEN = os.environ.get('GRAVEWRIGHT_RUNNER_TOKEN', '')
if not RUNNER_TOKEN:
    raise ImproperlyConfigured('Gravewright Runner must supply a startup token.')

# Database and media paths come from the project .env through config.settings.
# Runner state and collected assets remain separate from application storage.
if GRAVEWRIGHT_MODULES_ROOT is None:
    GRAVEWRIGHT_MODULES_ROOT = MEDIA_ROOT / 'modules'
STATIC_ROOT = RUNNER_DATA / 'staticfiles'
GRAVEWRIGHT_CONTENT_ROOT = RUNNER_DATA / 'compendiums'
ROOT_URLCONF = 'config.runner_urls'
ASGI_APPLICATION = 'config.runner_asgi.application'
