"""GM-only JSON library; exports contain layouts and never PDF bytes or actor values."""

from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError

from . import templates


@require_http_methods(["GET", "POST"])
def library(request, campaign_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        if request.method == "GET":
            result = templates.list_templates(campaign_id, request.user.pk)
        else:
            # A raw JSON file is escaped again inside the command envelope.
            if len(request.body) > 2 * templates.MAX_BUNDLE_BYTES + 4096:
                raise MapError("Use a mapping JSON file no larger than 1 MB.")
            import json
            try:
                payload = json.loads(request.body)
            except (ValueError, UnicodeError, RecursionError):
                raise MapError("Invalid PDF mapping JSON.") from None
            result = templates.command(campaign_id, request.user.pk, payload)
        response = JsonResponse(result)
        response["Cache-Control"] = "private, no-store"
        return response
    except (MapError, JournalError) as error:
        status = 403 if error.code in {"forbidden", "not_a_member"} else 409 if error.code == "conflict" else 404 if error.code == "not_found" else 400
        return JsonResponse({"message": str(error), "code": error.code}, status=status)


@require_GET
def export(request, campaign_id, template_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        row = templates.get_template(campaign_id, request.user.pk, template_id)
        response = JsonResponse(templates.normalize_bundle(row.bundle), json_dumps_params={"indent": 2, "ensure_ascii": False})
        response["Content-Disposition"] = f'attachment; filename="pdf-mapping-{row.pk}.json"'
        response["Cache-Control"] = "private, no-store"
        return response
    except (MapError, JournalError) as error:
        return JsonResponse({"message": str(error), "code": error.code}, status=403 if error.code in {"forbidden", "not_a_member"} else 404)
