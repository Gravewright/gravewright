from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET

from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError

from . import services


@require_GET
def state(request, campaign_id, map_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        return JsonResponse(services.state(campaign_id, request.user.pk, map_id))
    except JournalError, MapError:
        raise Http404 from None
