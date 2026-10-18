"""GM-only rehearsal and live-control endpoints over existing map services."""
import json

from django.views.decorators.http import require_GET, require_POST
from gravewright.journals.services import member

from . import blueprint_controls, blueprint_testing, services
from .builder import response
from .views import authorized


def _body(request):
    if len(request.body) > 1_100_000:
        raise services.MapError("The automation test command is too large.")
    try:
        return json.loads(request.body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise services.MapError("Invalid automation test command.") from None


@require_GET
def catalog(request, campaign_id):
    def read():
        from gravewright.actors.models import Actor
        who = member(campaign_id, request.user.pk)
        services.manage(who)
        return {"actors": [{"id": str(row.pk), "name": row.name}
                           for row in Actor.objects.filter(campaign_id=campaign_id).order_by("name", "id")]}
    return response(request, campaign_id, read)


@require_POST
def draft(request, campaign_id):
    return response(request, campaign_id, lambda: blueprint_testing.run_draft(campaign_id, request.user.pk, _body(request)))


def _scene(request, map_id, element_id, service):
    row = authorized(request, map_id)
    return response(request, row.campaign_id,
                    lambda: service(row.campaign_id, request.user.pk, row.pk, element_id, _body(request)))


@require_POST
def scene(request, map_id, element_id):
    return _scene(request, map_id, element_id, blueprint_testing.run)


@require_POST
def control(request, map_id, element_id):
    return _scene(request, map_id, element_id, blueprint_controls.control)
