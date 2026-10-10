"""Declarative, installation-wide language packs; no package Python is imported."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re

from .models import Package

PLACEHOLDERS = re.compile(r'\{[A-Za-z_][A-Za-z0-9_.]*\}')


@lru_cache(maxsize=1)
def reviewed_portuguese():
    """Host UI copy corrections, kept separate from signed module artifacts."""
    path = Path(__file__).with_name('locale_overrides') / 'pt-BR.json'
    return json.loads(path.read_text(encoding='utf-8'))


def validate_catalog(messages):
    from .packages import ModuleFailure
    if not isinstance(messages, dict) or not messages or len(messages) > 15000:
        raise ModuleFailure('invalid_data')
    for source, translation in messages.items():
        if (not isinstance(source, str) or not isinstance(translation, str)
                or not source.strip() or not translation.strip()
                or max(len(source), len(translation)) > 12000
                or sorted(PLACEHOLDERS.findall(source)) != sorted(PLACEHOLDERS.findall(translation))):
            raise ModuleFailure('invalid_data')


def catalogs():
    from .packages import compatible
    result = {'en': {'name': 'English', 'messages': {}}}
    for package in Package.objects.filter(global_enabled=True, revoked=False).order_by('pk'):
        if compatible(package.manifest.get('sdk', {}).get('requires')):
            result.update(deepcopy(package.locale_catalogs))
            if package.module_id == 'gravewright.translator' and 'pt-BR' in package.locale_catalogs:
                result['pt-BR']['messages'].update(reviewed_portuguese())
    return result


def for_request(request):
    if hasattr(request, '_gravewright_language'):
        return request._gravewright_language
    from django.conf import settings
    from gravewright.accounts.models import UserPreference
    from gravewright.administration.models import HostSettings
    available = catalogs()
    locale = request.get_signed_cookie('gravewright-language', default='')
    if request.user.is_authenticated:
        locale = UserPreference.objects.filter(user=request.user).values_list('locale', flat=True).first() or ''
    if not locale:
        locale = HostSettings.objects.filter(pk=1).values_list('default_locale', flat=True).first() or settings.DEFAULT_LOCALE
    locale = locale if locale in available else 'en'
    value = {'id': locale, 'messages': available[locale]['messages'],
             'options': [{'id': key, 'name': item['name']} for key, item in available.items()]}
    request._gravewright_language = value
    return value
