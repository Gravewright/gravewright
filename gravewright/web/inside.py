"""Composition of account and campaign workflows for the original Inside UI.

GPLv3 only, with the additional permission in LICENSE-EXCEPTION.
"""
import json
from pathlib import Path
import re

from datastar_py.django import DatastarResponse, ServerSentEventGenerator as SSE
from gravewright.accounts.client_ip import client_ip
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from gravewright.accounts import services as accounts
from gravewright.accounts.forms import AccountUpdateForm
from gravewright.accounts.models import UserPreference
from gravewright.accounts.views import MESSAGES as AUTH_TEXT, api_error, is_datastar, read_json
from gravewright.campaigns import services as campaigns
from gravewright.campaigns.catalog import list_rulesets
from gravewright.campaigns.models import Campaign
from gravewright.campaigns.forms import CampaignForm
from gravewright.campaigns.views import authenticated, validate_campaign_form
from .responses import navigate

TEXT = json.loads(Path(__file__).with_name('inside_messages.json').read_text())
SECTIONS = {'campaigns', 'settings', 'privacy', 'systems', 'addons', 'marketplace', 'administration'}


def inside_response(request, *, section='campaigns', dialog='', campaign=None, form=None,
                    error='', notice='', temporary_code='', joining=False):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    if section == 'marketplace':
        section = 'addons'
    if section not in SECTIONS or (request.user.role != 'owner' and section in ('privacy', 'systems', 'addons', 'marketplace', 'administration')):
        section = 'campaigns'
    rows = [campaigns.public_campaign(c) for c in Campaign.objects.visible_to(request.user).with_members()]
    query = request.GET.get('search', request.POST.get('_insideSearch', ''))
    system = request.GET.get('system', request.POST.get('_insideSystem', ''))
    visible = [row for row in rows if (not system or row['system'] == system) and
               query.strip().lower() in f"{row['name']} {row['description']}".lower()]
    selected = campaigns.public_campaign(campaign) if campaign else None
    rulesets = list_rulesets()
    dialog_rulesets = list(rulesets)
    if campaign and campaign.system and campaign.system not in {row['systemId'] for row in rulesets}:
        dialog_rulesets.append({'systemId': campaign.system, 'title': f'{campaign.system} (unavailable)'})
    if form:
        fields = {k: form.data.get(k, '') for k in ['name', 'description', 'system', 'image', 'code']}
    else:
        fields = {k: (selected or {}).get(k, '') or '' for k in ['name', 'description', 'system', 'image', 'code']}
        if not campaign:
            fields['system'] = rulesets[0]['systemId']
    from gravewright.administration.preferences import read as host_preferences
    context = {
        'privacy_policy': host_preferences()['privacy'] if section == 'privacy' else {},
        **TEXT, 'auth': AUTH_TEXT, 'user': request.user, 'owner': request.user.role == 'owner',
        'section': section, 'rows': rows, 'visible_rows': visible, 'rulesets': rulesets,
        'dialog_rulesets': dialog_rulesets,
        'system_titles': {r['systemId']: r['title'] for r in rulesets},
        'search': query, 'system_filter': system,
        'dialog': dialog, 'selected': selected, 'fields': fields,
        'error': error, 'notice': notice, 'temporary_code': temporary_code,
        'joining': joining, 'ping_color': UserPreference.objects.filter(user=request.user).values_list('ping_color', flat=True).first() or '#f2c679',
    }
    from .localization import template_context
    context.update(template_context(request))
    if is_datastar(request):
        html = render_to_string('gravewright_web/inside/shell.html', context, request=request, using='jinja2')
        events = [SSE.patch_elements(html)]
        if section == 'settings' and notice:
            events.append(SSE.patch_signals({'_newPassword': '', '_currentPassword': '', '_confirmPassword': ''}))
        return DatastarResponse(iter(events))
    return render(request, 'gravewright_web/inside/page.html', context, using='jinja2')


@require_GET
def inside(request):
    return inside_response(request, section=request.GET.get('section', 'campaigns'),
                           joining=request.GET.get('join') == '1')


@require_GET
def dialog(request, mode, campaign_id=None):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    if mode not in {'create', 'edit', 'invite', 'remove', 'preview'}:
        return api_error(accounts.AuthError('invalid_input', 404))
    try:
        if mode == 'create' and request.user.role != 'owner':
            raise accounts.AuthError('owner_required', 403)
        campaign = campaigns.get_campaign(request.user, campaign_id, manage=mode != 'preview') if campaign_id else None
        if mode != 'create' and campaign is None:
            raise accounts.AuthError('container_not_found', 404)
        return inside_response(request, dialog=mode, campaign=campaign)
    except accounts.AuthError as error:
        return api_error(error)


@require_POST
def save_campaign(request, campaign_id=None):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    existing = None
    data = request.POST.dict()
    try:
        if campaign_id:
            existing = campaigns.get_campaign(request.user, campaign_id, manage=True)
        elif request.user.role != 'owner':
            raise accounts.AuthError('owner_required', 403)
        form = validate_campaign_form(data, request.FILES, instance=existing)
        campaigns.save_campaign(request.user, form, existing=existing)
    except accounts.AuthError as error:
        if error.status in (403, 404):
            return api_error(error)
        # A minimal bound form retains the submitted public fields, never secrets.
        return inside_response(request, dialog='edit' if existing else 'create', campaign=existing,
                               form=CampaignForm(data, instance=existing), error=AUTH_TEXT['errors'].get(error.code, AUTH_TEXT['errors']['request_failed']))
    return inside_response(request)


@require_POST
def issue_code(request, campaign_id, kind):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    try:
        issued = campaigns.issue_code(request.user, campaign_id, kind)
        campaign = campaigns.get_campaign(request.user, campaign_id, manage=True)
        return inside_response(request, dialog=kind, campaign=campaign, temporary_code=issued['code'])
    except accounts.AuthError as error:
        return api_error(error)


@require_POST
def remove(request, campaign_id):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    try:
        campaigns.delete_campaign(request.user, campaign_id, request.POST.get('code', ''))
    except accounts.AuthError as error:
        if error.status in (403, 404):
            return api_error(error)
        return inside_response(request, dialog='remove', campaign=campaigns.get_campaign(request.user, campaign_id),
                               temporary_code=request.POST.get('display_code', ''),
                               error=AUTH_TEXT['errors'].get(error.code, AUTH_TEXT['errors']['request_failed']))
    return inside_response(request)


@require_POST
def join(request):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    try:
        campaigns.join_campaign(request.user, request.POST.get('code', ''), client_ip(request))
    except accounts.AuthError as error:
        response = inside_response(request, joining=True, error=AUTH_TEXT['errors'].get(error.code, AUTH_TEXT['errors']['request_failed']))
        if error.retry_after:
            response['Retry-After'] = str(error.retry_after)
        return response
    return inside_response(request)


@sensitive_post_parameters('currentPassword', 'newPassword', 'confirmPassword')
@require_POST
def save_account(request):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    data = request.POST.dict()
    new_password = data.get('newPassword', '')
    if new_password != data.get('confirmPassword', ''):
        return inside_response(request, section='settings', error='The new passwords do not match.')
    try:
        accounts.reserve_attempt(request)
        if 'email' in data and not data['email'].strip():
            raise accounts.AuthError('invalid_email')
        form = AccountUpdateForm(data)
        if not form.is_valid():
            raise accounts.AuthError('invalid_email' if 'email' in form.errors else 'invalid_input')
        accounts.update_account(request, form.cleaned_data, change_password=bool(new_password))
    except accounts.AuthError as error:
        message = ('The current password is incorrect.' if error.code == 'invalid_credentials'
                   else AUTH_TEXT['errors'].get(error.code, 'Could not save the account. Check your entries and try again.'))
        return inside_response(request, section='settings', error=message)
    message = 'Account saved. Other sessions have been signed out.' if new_password else 'Profile saved.'
    return inside_response(request, section='settings', notice=message)


@require_http_methods(['GET', 'POST'])
@authenticated
def preferences(request):
    if request.method == 'POST':
        data = request.POST.dict() if is_datastar(request) else read_json(request)
        color = data.get('pingColor')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise accounts.AuthError('invalid_ping_color')
        UserPreference.objects.update_or_create(user=request.user, defaults={'ping_color': color.lower()})
        if is_datastar(request):
            return DatastarResponse(SSE.patch_signals({'_pingNotice': 'Color saved for your account.'}))
    color = UserPreference.objects.filter(user=request.user).values_list('ping_color', flat=True).first() or '#f2c679'
    return JsonResponse({'pingColor': color})


@require_POST
@authenticated
def language(request):
    from django.conf import settings
    from gravewright.modules.localization import catalogs
    locale = request.POST.get('locale', '')
    available = catalogs()
    if len(available) < 2 or locale not in available:
        return api_error(accounts.AuthError('invalid_locale'))
    UserPreference.objects.update_or_create(user=request.user, defaults={'locale': locale})
    response = navigate(request, '/inside?section=settings')
    response.set_signed_cookie('gravewright-language', locale, max_age=365 * 24 * 3600,
                               secure=settings.SESSION_COOKIE_SECURE, httponly=True, samesite='Strict')
    return response
