"""HTTP campaign preparation shell; no live-table connection is established."""

import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from gravewright.accounts.services import AuthError
from gravewright.accounts.views import api_error
from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError
from gravewright.web.localization import template_context
from gravewright.web.responses import navigate

from . import management
from .systems import resolve_system_id, sheet_provider


@cache_control(private=True, no_store=True)
@require_GET
@ensure_csrf_cookie
def page(request, campaign_id):
    if not request.user.is_authenticated:
        return navigate(request, '/login')
    try:
        loaded = management.load(request.user, campaign_id)
        campaign, ruleset = loaded['campaign'], loaded['ruleset']
        from gravewright.actors import services as actors
        from gravewright.journals import services as journals
        from gravewright.maps import services as maps
        from gravewright.table.domain import state
        initial_content = {
            'maps': maps.state(campaign.pk, request.user.pk),
            'actors': actors.state(campaign.pk, request.user.pk),
            'journals': journals.state(campaign.pk, request.user.pk),
            'items': state(campaign.pk, request.user.pk, 'items'),
        }
    except (AuthError, JournalError, MapError):
        return HttpResponse(status=404)

    from gravewright.table.views import DOCK, TEXT, TOOL_TEXT
    context = {
        **TEXT,
        't': lambda key: TOOL_TEXT.get(key, key),
        'actor_sheet_provider': sheet_provider(campaign.system),
        'system_id': resolve_system_id(campaign.system),
        'ruleset': ruleset,
        'renderer_debug': settings.APP_DEBUG,
        'command_palette_enabled': settings.COMMAND_PALETTE_ENABLED,
        'lobby_enabled': settings.LOBBY_READY_CHECK_ENABLED,
        'detached_chat': False,
        'campaign': campaign,
        'owner': True,
        'member_role': 'gm',
        'layers': DOCK['layers'],
        'tools': DOCK['tools'],
        'directories': [directory for directory in DOCK['directories']
                        if directory['id'] != 'items' or ruleset.get('itemTypes')],
        'initial_content': initial_content,
        'has_scenes': bool(initial_content['maps']['maps']),
        'has_actors': bool(initial_content['actors']['actors']),
        'management_overview': loaded['overview'],
        'management_api_url': reverse('campaigns:management', args=[campaign.pk]),
        'csrfCookie': get_token(request),
        'csrf_cookie_name': settings.CSRF_COOKIE_NAME,
    }
    context.update(template_context(request))
    return render(request, 'gravewright_web/campaign_manager/page.html', context, using='jinja2')


@cache_control(private=True, no_store=True)
@require_GET
def overview(request, campaign_id):
    try:
        return JsonResponse(management.overview(request.user, campaign_id))
    except AuthError as error:
        return api_error(error)


def _respond(work):
    from .preparation import PreparationError
    try:
        return JsonResponse(work())
    except PreparationError as error:
        return JsonResponse({'error': error.message, 'code': error.code}, status=error.status)
    except AuthError as error:
        return api_error(error)


@cache_control(private=True, no_store=True)
@require_http_methods(['GET', 'POST'])
def preparation(request, campaign_id):
    from . import preparation as service
    if request.method == 'GET':
        return _respond(lambda: service.state(request.user, campaign_id))
    def command():
        try:
            body = json.loads(request.body or b'{}')
        except (ValueError, UnicodeDecodeError):
            raise service.PreparationError('Invalid preparation command.') from None
        if not isinstance(body, dict):
            raise service.PreparationError('Invalid preparation command.')
        if not request.user.is_authenticated:
            raise AuthError('authentication_required', 401)
        return service.command(request.user, campaign_id, body.get('action'), body.get('payload'), body.get('request_id'))
    return _respond(command)


@cache_control(private=True, no_store=True)
@require_GET
def references(request, campaign_id):
    from . import preparation as service
    return _respond(lambda: service.references(request.user, campaign_id, request.GET.get('type'), request.GET.get('id', '')))


@cache_control(private=True, no_store=True)
@require_GET
def view_as(request, campaign_id, user_id):
    from . import preparation as service
    return _respond(lambda: service.view_as(request.user, campaign_id, str(user_id)))


@cache_control(private=True, no_store=True)
@require_GET
def journal_history(request, campaign_id, journal_id):
    from . import preparation as service
    return _respond(lambda: service.journal_history(request.user, campaign_id, str(journal_id)))


@cache_control(private=True, no_store=True)
@require_GET
def journal_revision(request, campaign_id, revision_id):
    from . import preparation as service
    return _respond(lambda: service.compare(request.user, campaign_id, str(revision_id)))


@cache_control(private=True, no_store=True)
@require_GET
def journal_trash(request, campaign_id):
    from . import preparation as service
    return _respond(lambda: service.trash(request.user, campaign_id))
