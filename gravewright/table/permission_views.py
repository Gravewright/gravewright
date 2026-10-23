"""Native ownership editor transport over the public ownership service."""
import json
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from gravewright.journals.services import JournalError
from . import permission_services
# Retain trusted internal imports used by journal presentation grants.
from .permission_services import resolve, children, snapshot, store


@require_http_methods(["GET", "POST"])
def document_permissions(request, campaign_id, kind, resource_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=403)
    try:
        if request.method == "POST":
            try:
                payload = json.loads(request.body)
            except (ValueError, UnicodeError, RecursionError):
                raise JournalError("Invalid resource permissions.") from None
            request_id = (payload.get("requestId") or uuid.uuid4()) if isinstance(payload, dict) else uuid.uuid4()
            result = permission_services.command(campaign_id, request.user.pk, kind, resource_id, payload, request_id)
        else:
            result = permission_services.state(campaign_id, request.user.pk, kind, resource_id)
        response = JsonResponse(result)
        response["Cache-Control"] = "private, no-store"
        return response
    except JournalError as error:
        status = {"not_found": 404, "forbidden": 403, "not_a_member": 403, "conflict": 409}.get(error.code, 400)
        return JsonResponse({"error": str(error)}, status=status)
