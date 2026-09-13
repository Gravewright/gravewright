"""Compose Django, storage, authentication and realtime configuration.

Load literal .env defaults before validating engine limits in config.engine.
Process environment variables win. SQLite stores durable state; Channels uses
memory in development or the guarded local Runner and Redis for public hosting.
See docs/en/configuration.md and docs/en/deployment.md for server configuration.
"""

import os
import sys
from pathlib import Path

from config.environment import env_bool, env_path, load_environment, public_origin

# All relative configuration paths resolve against the source tree root.
BASE_DIR = Path(__file__).resolve().parent.parent
# The local Runner prepares its own user configuration before importing Django.
# Never mix a developer/production checkout's .env into that private profile.
_LOCAL_RUNNER = os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.runner'
if not _LOCAL_RUNNER:
    load_environment()
from config.engine import configure
globals().update(configure())


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-local-gravewright-development-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DJANGO_DEBUG', True)
if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise ValueError('Set DJANGO_SECRET_KEY when DJANGO_DEBUG=false.')

GRAVEWRIGHT_HOST = os.environ.get('GRAVEWRIGHT_HOST', '127.0.0.1').strip()
GRAVEWRIGHT_PORT = int(os.environ.get('GRAVEWRIGHT_PORT', '3000'))
if not GRAVEWRIGHT_HOST or not 1 <= GRAVEWRIGHT_PORT <= 65535:
    raise ValueError('Set GRAVEWRIGHT_HOST and a GRAVEWRIGHT_PORT between 1 and 65535.')
GRAVEWRIGHT_PUBLIC_ORIGIN, public_host = public_origin()
ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    'DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,[::1]'
).split(',') if host.strip()]
if public_host and public_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(public_host)
CSRF_TRUSTED_ORIGINS = [GRAVEWRIGHT_PUBLIC_ORIGIN] if GRAVEWRIGHT_PUBLIC_ORIGIN else []


# Daphne supplies the ASGI-aware development server. Domain apps own their
# models, migrations and static assets; their labels are part of archive formats.

INSTALLED_APPS = [
    'daphne',
    'gravewright.items',
    'gravewright.audio',
    'gravewright.cards',
    'gravewright.combat',
    'gravewright.compendiums',

    'gravewright.administration',
    'gravewright.modules',
    'gravewright.realtime.apps.RealtimeConfig',
    'gravewright.chat.apps.ChatConfig',
    'gravewright.dice.apps.DiceConfig',
    'gravewright.journals.apps.JournalsConfig',
    'gravewright.maps.apps.MapsConfig',
    'gravewright.actors',
    'gravewright.tokens',
    'gravewright.pdf_system',
    'gravewright.accounts.apps.AccountsConfig',
    'gravewright.web.apps.WebConfig',
    'gravewright.campaigns.apps.CampaignsConfig',
    'gravewright.table.apps.TableConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Trusted Python extensions are explicitly installed by the host operator.
# Browser marketplace archives never populate this setting or import Python.
GRAVEWRIGHT_SERVER_APP_PATHS = tuple(dict.fromkeys(
    value.strip() for value in os.environ.get('GRAVEWRIGHT_SERVER_APP_PATHS', '').split(os.pathsep)
    if value.strip()
))
for value in GRAVEWRIGHT_SERVER_APP_PATHS:
    app_path = Path(value).expanduser()
    app_path = (app_path if app_path.is_absolute() else BASE_DIR / app_path).resolve()
    if not app_path.is_dir():
        raise ValueError(f'GRAVEWRIGHT_SERVER_APP_PATHS directory does not exist: {app_path}')
    if str(app_path) not in sys.path:
        sys.path.append(str(app_path))
GRAVEWRIGHT_SERVER_APPS = tuple(dict.fromkeys(
    name.strip() for name in os.environ.get('GRAVEWRIGHT_SERVER_APPS', '').split(',')
    if name.strip()
))
INSTALLED_APPS += [name for name in GRAVEWRIGHT_SERVER_APPS if name not in INSTALLED_APPS]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'gravewright.accounts.middleware.AuthSecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'gravewright.campaigns.streamer.StreamerMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'NAME': 'jinja2',
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'environment': 'config.jinja2.environment',
                    'context_processors':['gravewright.administration.preferences.template_context',
                                          'gravewright.web.localization.template_context']},
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': (':memory:' if os.environ.get('GRAVEWRIGHT_DATABASE') == ':memory:'
                 else env_path('GRAVEWRIGHT_DATABASE', 'data/gravewright.sqlite3')),
        'OPTIONS': {'timeout': DATABASE_POOL_TIMEOUT, 'transaction_mode': 'IMMEDIATE'},
        # File-backed SQLite exercises the same locking as development.
        'TEST': {'NAME': BASE_DIR / 'data' / 'test-gravewright.sqlite3'},
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

# VTT ownership is User.role; Django is_staff/is_superuser remain separate.
AUTH_USER_MODEL = 'gravewright_accounts.User'
AUTH_PASSWORD_VALIDATORS = [{
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    'OPTIONS': {'min_length': 12},
}]
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.ScryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/inside'
LOGOUT_REDIRECT_URL = '/login'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = (GRAVEWRIGHT_PUBLIC_ORIGIN.startswith('https://')
                         or env_bool('DJANGO_SECURE_COOKIES', False))
SESSION_COOKIE_NAME = ('__Host-' if SESSION_COOKIE_SECURE else '') + 'gravewright-session'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_NAME = ('__Host-' if CSRF_COOKIE_SECURE else '') + 'gravewright-csrf'
CSRF_HEADER_NAME = 'HTTP_X_CSRF_TOKEN'
CSRF_FAILURE_VIEW = 'gravewright.accounts.views.csrf_failure'
SECURE_HSTS_SECONDS = 31536000 if SESSION_COOKIE_SECURE else 0
SECURE_REFERRER_POLICY = 'no-referrer'
X_FRAME_OPTIONS = 'DENY'
GRAVEWRIGHT_AUTH_MAX_ATTEMPTS = int(os.environ.get('GRAVEWRIGHT_AUTH_MAX_ATTEMPTS', '30'))
GRAVEWRIGHT_AUTH_WINDOW_SECONDS = int(os.environ.get('GRAVEWRIGHT_AUTH_WINDOW_SECONDS', '300'))
if min(GRAVEWRIGHT_AUTH_MAX_ATTEMPTS, GRAVEWRIGHT_AUTH_WINDOW_SECONDS) < 1:
    raise ValueError('Authentication rate limits must be positive.')


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = DEFAULT_LOCALE

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Assets and installed module packages are private and served by guarded views.
# Never expose this directory as an unauthenticated /media/ static location.
MEDIA_ROOT = env_path('GRAVEWRIGHT_MEDIA_ROOT', 'data/media')
GRAVEWRIGHT_CONTENT_ROOT = env_path('GRAVEWRIGHT_CONTENT_ROOT', 'data/vtt/compendiums')
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
GRAVEWRIGHT_MAP_MAX_PIXELS = int(os.environ.get('GRAVEWRIGHT_MAP_MAX_PIXELS', '64000000'))


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


# Memory delivery is limited to development and the guarded local Runner.
# config.runner validates the local profile; public hosting still requires Redis.
GRAVEWRIGHT_REDIS_URL = os.environ.get('GRAVEWRIGHT_REDIS_URL', '')
if GRAVEWRIGHT_REDIS_URL:
    CHANNEL_LAYERS = {'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [GRAVEWRIGHT_REDIS_URL]},
    }}
else:
    if not DEBUG and not _LOCAL_RUNNER:
        raise ValueError('Set GRAVEWRIGHT_REDIS_URL for realtime in production.')
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
GRAVEWRIGHT_HEARTBEAT_SECONDS = 5
GRAVEWRIGHT_PRESENCE_TTL = 20

GRAVEWRIGHT_MARKETPLACE_URL = os.environ.get("GRAVEWRIGHT_MARKETPLACE_URL", "")
GRAVEWRIGHT_MARKETPLACE_KEYS_FILE = (
    str(env_path('GRAVEWRIGHT_MARKETPLACE_KEYS_FILE', ''))
    if os.environ.get('GRAVEWRIGHT_MARKETPLACE_KEYS_FILE', '').strip() else ''
)

if DATABASE_ECHO:
    LOGGING = {
        'version': 1, 'disable_existing_loggers': False,
        'handlers': {'sql_console': {'class': 'logging.StreamHandler'}},
        'loggers': {'django.db.backends': {'handlers': ['sql_console'], 'level': 'DEBUG', 'propagate': False}},
    }

# Django source releases; empty until this distribution publishes compatible artifacts.
GRAVEWRIGHT_RELEASES_REPOSITORY = os.environ.get("GRAVEWRIGHT_RELEASES_REPOSITORY", "Gravewright/gravewright")
