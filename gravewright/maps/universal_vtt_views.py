"""GM-only Universal VTT interchange endpoints for native scenes."""
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from gravewright.journals.services import member
from . import services, universal_vtt
from .builder import response
from .views import authorized


@require_POST
def import_map(request, campaign_id):
    def operation():
        who = member(campaign_id, request.user.pk)
        services.manage(who)
        upload = request.FILES.get("file")
        limit = min(universal_vtt.MAX_JSON_BYTES, settings.MAP_UPLOAD_MAX_BYTES)
        if upload is None:
            raise services.MapError("Choose a valid Universal VTT 0.2 or 0.3 file.")
        if upload.size > limit:
            raise services.MapError("The Universal VTT file exceeds the interchange size limit.")
        editable = request.POST.get("builderEditable", "false")
        if editable not in ("true", "false"):
            raise services.MapError("Invalid Universal VTT import mode.")
        return universal_vtt.import_map(campaign_id, request.user.pk, upload.read(limit + 1),
            name=request.POST.get("name", ""), request_id=request.POST.get("request_id"),
            folder_id=request.POST.get("folderId") or None, builder_editable=editable == "true")
    return response(request, campaign_id, operation)


@require_GET
def export_map(request, map_id):
    scene = authorized(request, map_id)
    return response(request, scene.campaign_id,
                    lambda: universal_vtt.export_map(scene.campaign_id, request.user.pk, scene.pk))
