from django.conf import settings
from gravewright.web.assets import static, module_import_map
from django.urls import reverse
from jinja2 import Environment
from gravewright.web.iconography import icon, rpg_icon
from gravewright.version import release_label
from gravewright.web.localization import LocalizationExtension, tr


def environment(**options):
    env = Environment(extensions=[LocalizationExtension], **options)
    env.globals['tr'] = tr
    env.globals['module_import_map'] = module_import_map
    env.globals.update(static=static, url=reverse, icon=icon, rpg_icon=rpg_icon, app_name=settings.APP_NAME,
                       default_locale=settings.DEFAULT_LOCALE, release_label=release_label())
    return env
