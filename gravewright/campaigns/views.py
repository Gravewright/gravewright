from functools import wraps

from gravewright.accounts.client_ip import client_ip
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from gravewright.accounts.services import AuthError
from gravewright.accounts.views import api_error, read_json
from . import services
from .catalog import RULESETS
from .forms import CampaignForm
from .models import Campaign


def authenticated(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return api_error(AuthError('authentication_required', 401))
        try:
            return view(request, *args, **kwargs)
        except AuthError as error:
            return api_error(error)
    return wrapped


def validate_campaign_form(data, files=None, *, instance=None):
    if any(not isinstance(data.get(key, ''), str) for key in ('name', 'description', 'system', 'image')):
        raise AuthError('invalid_input')
    form = CampaignForm(data, files, instance=instance)
    if not form.is_valid():
        key = next(iter(form.errors))
        key = 'image' if key in ('cover', 'image') else key
        raise AuthError(f'invalid_container_{key}')
    return form


@require_http_methods(['GET', 'POST'])
@authenticated
def containers(request):
    if request.method == 'GET':
        return JsonResponse([services.public_campaign(c) for c in
                             Campaign.objects.visible_to(request.user).with_members()], safe=False)
    if request.user.role != 'owner':
        raise AuthError('owner_required', 403)
    form = validate_campaign_form(read_json(request))
    return JsonResponse(services.public_campaign(services.save_campaign(request.user, form)), status=201)


@require_POST
@authenticated
def update(request, campaign_id):
    campaign = services.get_campaign(request.user, campaign_id, manage=True)
    form = validate_campaign_form(read_json(request), instance=campaign)
    return JsonResponse(services.public_campaign(services.save_campaign(request.user, form, existing=campaign)))


@require_POST
@authenticated
def code(request, campaign_id, kind):
    services.get_campaign(request.user,campaign_id,manage=True)
    data=read_json(request) if request.body else {}
    if set(data)-{'expires_in_hours','max_uses'}:raise AuthError('invalid_input')
    return JsonResponse(services.issue_code(request.user,campaign_id,kind,**data))


@require_POST
@authenticated
def join(request):
    data = read_json(request)
    campaign = services.join_campaign(request.user, data.get('code', ''), client_ip(request))
    return JsonResponse(services.public_campaign(campaign))


@require_POST
@authenticated
def remove(request, campaign_id):
    services.delete_campaign(request.user, campaign_id, read_json(request).get('code', ''))
    return HttpResponse(status=204)


@require_GET
@authenticated
def cover(request, campaign_id):
    campaign = services.get_campaign(request.user, campaign_id)
    if not campaign.cover:
        raise AuthError('container_not_found', 404)
    try:
        return FileResponse(campaign.cover.open('rb'))
    except FileNotFoundError:
        raise AuthError('container_not_found', 404) from None


@require_GET
@authenticated
def rulesets(request):
    return JsonResponse({'rulesets': RULESETS})


@require_GET
@authenticated
def invitation_status(request,campaign_id):
    return JsonResponse(services.code_status(request.user,campaign_id))


@require_POST
@authenticated
def revoke_invitation_code(request,campaign_id):
    return JsonResponse(services.code_status(request.user,campaign_id,revoke=True))


@require_POST
@authenticated
def ban_member(request, campaign_id):
    result=services.ban_member(request.user, campaign_id, read_json(request).get('user_id'))
    from gravewright.administration.views import audit
    audit(request,'membership.banned',campaign_id=str(campaign_id),target_user_id=result['removed'])
    return JsonResponse(result)


@require_http_methods(['GET','POST'])
@authenticated
def onboarding(request,campaign_id):
    from . import onboarding as service
    if request.method=='GET':return JsonResponse(service.state(request.user,campaign_id))
    return JsonResponse(service.preference(request.user,campaign_id,read_json(request).get('dismissed')))


@require_POST
@authenticated
def player_onboarding(request,campaign_id):
    from .onboarding import claim
    return JsonResponse(claim(request.user,campaign_id))


@require_POST
@authenticated
def streamer_link(request,campaign_id):
    from .streamer import issue
    result=issue(request.user,campaign_id)
    result['url']=request.build_absolute_uri(result['url'])
    return JsonResponse(result)


@require_POST
@authenticated
def revoke_streamer(request,campaign_id):
    from .streamer import revoke
    return JsonResponse(revoke(request.user,campaign_id))
