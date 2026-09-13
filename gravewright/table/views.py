"""Render the table shell and expose authorized resource/member state over HTTP."""

import json
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from gravewright.accounts.services import AuthError
from gravewright.campaigns.services import get_campaign
from gravewright.web.responses import navigate

ROOT = Path(__file__).parent
DOCK = json.loads((ROOT / "dock.json").read_text())
TOOL_TEXT = json.loads((ROOT / 'tool_messages.json').read_text())
TEXT = json.loads((ROOT / "messages.json").read_text())


@require_GET
@ensure_csrf_cookie
def table(request, campaign_id, detached_chat=False):
    if not request.user.is_authenticated:
        return navigate(request, "/login")
    try:
        campaign = get_campaign(request.user, campaign_id)
    except AuthError:
        raise Http404 from None
    owner = any(
        m.user_id == request.user.pk and m.role == "gm"
        for m in campaign.memberships.all()
    )
    layers = DOCK["layers"] if owner else DOCK["layers"][:1]
    context = {
        **TEXT,
        't': lambda key: TOOL_TEXT.get(key, key),
        'renderer_debug': settings.APP_DEBUG,
        'command_palette_enabled': settings.COMMAND_PALETTE_ENABLED,
        'lobby_enabled': settings.LOBBY_READY_CHECK_ENABLED,
        "detached_chat": detached_chat,
        "campaign": campaign,
        "owner": owner,
        "member_role": next(m.role for m in campaign.memberships.all() if m.user_id == request.user.pk),
        "layers": layers,
        "tools": {
            layer["id"]: [
                tool
                for tool in DOCK["tools"][layer["id"]]
                if owner or tool["id"] != "visibility"
            ]
            for layer in layers
        },
        # The original catalog has no item capability without a system module.
        "directories": [
            p
            for p in DOCK["directories"]
            if owner or p["id"] not in {"scenes"}
        ],
    }
    from gravewright.web.localization import template_context
    context.update(template_context(request))
    return render(request, "gravewright_table/page.html", context, using="jinja2")


@require_GET
def module_state(request,campaign_id,module):
    from .domain import state
    from gravewright.maps.services import MapError
    from gravewright.journals.services import JournalError
    from django.http import JsonResponse
    if not request.user.is_authenticated:return JsonResponse({'error':'Authentication required.'},status=403)
    try:return JsonResponse(state(campaign_id,request.user.pk,module,request.GET.get('sceneId') or None,request.GET.get('previewTokenId') or None))
    except (MapError,JournalError) as error:return JsonResponse({'error':str(error)},status=403)


@require_GET
def permission_members(request,campaign_id):
    from django.http import JsonResponse
    from gravewright.journals.services import member,JournalError
    from gravewright.campaigns.models import Membership
    try:
        if not request.user.is_authenticated or member(campaign_id,request.user.pk).role!='gm':raise Http404
        return JsonResponse({'members':[{'id':str(m.user_id),'name':m.user.name} for m in Membership.objects.filter(campaign_id=campaign_id).select_related('user')]})
    except JournalError:raise Http404 from None
