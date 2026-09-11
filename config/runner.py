"""Private, single-process desktop profile selected by Gravewright Runner.

The launcher supplies isolated environment values and holds the data-directory
lock. This profile deliberately serves only the local machine. Public hosting
continues to use config.settings with Redis and a TLS proxy.
"""

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


_data = os.environ.get('GRAVEWRIGHT_RUNNER_DATA', '')
_origin = f'http://127.0.0.1:{GRAVEWRIGHT_PORT}'
if (not _data or not Path(_data).is_absolute() or DEBUG
        or GRAVEWRIGHT_HOST != '127.0.0.1'
        or GRAVEWRIGHT_PUBLIC_ORIGIN != _origin
        or ALLOWED_HOSTS != ['127.0.0.1'] or TRUSTED_PROXIES
        or GRAVEWRIGHT_REDIS_URL or SESSION_COOKIE_SECURE):
    raise ImproperlyConfigured('Start the local profile with Gravewright Runner.')

RUNNER_DATA = Path(_data).resolve()
RUNNER_TOKEN = os.environ.get('GRAVEWRIGHT_RUNNER_TOKEN', '')
if not RUNNER_TOKEN:
    raise ImproperlyConfigured('Gravewright Runner must supply a startup token.')

# BASE_DIR remains the source checkout for templates, contracts and version data.
# Every writable application directory belongs to the selected user-data folder.
DATABASES['default']['NAME'] = RUNNER_DATA / 'gravewright.sqlite3'
DATABASES['default']['TEST']['NAME'] = RUNNER_DATA / 'test-gravewright.sqlite3'
MEDIA_ROOT = RUNNER_DATA / 'media'
STATIC_ROOT = RUNNER_DATA / 'staticfiles'
GRAVEWRIGHT_CONTENT_ROOT = RUNNER_DATA / 'compendiums'
ROOT_URLCONF = 'config.runner_urls'
ASGI_APPLICATION = 'config.runner_asgi.application'
