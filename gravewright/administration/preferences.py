"""Persisted host preferences, separate from personal account settings."""
from copy import deepcopy
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from gravewright.accounts.services import AuthError
from .models import HostSettings

DEFAULT_PRIVACY = {
    "enabled": False,
    "title": "Política de Privacidade",
    "content": "",
    "data_controller": "",
    "dpo_contact": "",
    "contact_email": "",
    "legal_basis": "Consentimento, execução de contrato e legítimo interesse, conforme aplicável.",
    "retention_policy": "Os dados são mantidos pelo tempo necessário para operar o serviço e cumprir obrigações legais.",
    "data_subject_rights": "O titular pode solicitar acesso, correção, portabilidade, revogação de consentimento e exclusão de dados.",
    "updated_at": None,
}


CHANNELS = {'stable','testing','dev'}
SUPPORTED_LOCALES = ('en',)


def read():
    row=HostSettings.objects.filter(pk=1).first() or HostSettings()
    locale=row.default_locale or settings.DEFAULT_LOCALE
    if locale not in SUPPORTED_LOCALES:locale=SUPPORTED_LOCALES[0]
    privacy={**deepcopy(DEFAULT_PRIVACY),**row.privacy}
    privacy['enabled']=bool(settings.PRIVACY_ENABLED or privacy['enabled'])
    return {'app':{'app_name':row.app_name or settings.APP_NAME,
                   'default_locale':locale,
                   'supported_locales':list(SUPPORTED_LOCALES)},
            'updates':{'core_channel':row.channel,'packages_channel':row.channel if row.channels_linked else row.packages_channel,'channels_linked':row.channels_linked},
            'privacy':privacy}


@transaction.atomic
def update(user, section, data):
    if not user.is_authenticated or user.role!='owner':raise AuthError('owner_required',403)
    if not isinstance(data,dict):raise AuthError('invalid_input')
    row,_=HostSettings.objects.select_for_update().get_or_create(pk=1)
    if section=='app':
        if set(data)-{'app_name','default_locale','core_channel','packages_channel','channels_linked'}:raise AuthError('invalid_input')
        for field,limit in [('app_name',80),('default_locale',16)]:
            if field in data:
                value=data[field]
                if not isinstance(value,str) or len(value.strip())>limit:raise AuthError('invalid_input')
                if field=='default_locale' and value not in SUPPORTED_LOCALES:raise AuthError('invalid_locale')
                setattr(row,field,value.strip())
        for field,target in [('core_channel','channel'),('packages_channel','packages_channel')]:
            if field in data:
                if not isinstance(data[field],str) or data[field] not in CHANNELS:raise AuthError('invalid_channel')
                setattr(row,target,data[field])
        if 'channels_linked' in data:
            if type(data['channels_linked']) is not bool:raise AuthError('invalid_input')
            row.channels_linked=data['channels_linked']
        if row.channels_linked:row.packages_channel=row.channel
        row.update_status={}
    elif section=='privacy':
        if set(data)-set(DEFAULT_PRIVACY) or 'updated_at' in data:raise AuthError('invalid_input')
        privacy={**deepcopy(DEFAULT_PRIVACY),**row.privacy}
        for field,value in data.items():
            if field=='enabled':
                if type(value) is not bool:raise AuthError('invalid_input')
            else:
                limit=120 if field=='title' else 160 if field in ('data_controller','dpo_contact','contact_email') else 20000
                if not isinstance(value,str) or len(value)>limit:raise AuthError('invalid_input')
                value=value.strip()
                if field=='contact_email' and value:
                    try:validate_email(value)
                    except ValidationError:raise AuthError('invalid_email') from None
            privacy[field]=value
        privacy['title']=privacy['title'] or DEFAULT_PRIVACY['title']
        privacy['updated_at']=timezone.now().date().isoformat()
        row.privacy=privacy
    else:raise AuthError('not_found',404)
    row.save()
    return read()


def public_privacy():
    privacy=read()['privacy']
    if not privacy['enabled']:return {'enabled':False}
    return privacy


def template_context(request):
    values=read()['app']
    return {'app_name':values['app_name'],'default_locale':values['default_locale']}
