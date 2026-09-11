from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from gravewright.web.iconography import icon
from gravewright.version import release_label


def environment(**options):
    env = Environment(**options)
    env.globals.update(static=static, url=reverse, icon=icon, app_name=settings.APP_NAME,
                       default_locale=settings.DEFAULT_LOCALE, release_label=release_label())
    return env
