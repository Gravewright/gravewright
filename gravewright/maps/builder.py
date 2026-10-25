"""Independent GM map editor and campaign-scoped editable project endpoints."""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from gravewright.journals.services import JournalError, member
from gravewright.web.localization import template_context
from gravewright.web.responses import navigate

from . import blueprint_templates, builder_services, services
from . import builder_presets


@require_http_methods(["GET", "POST"])
def object_presets(request, campaign_id):
    return response(request, campaign_id, lambda: builder_presets.catalog(campaign_id, request.user.pk)
                    if request.method == "GET" else builder_presets.save(campaign_id, request.user.pk, body(request)))


@require_http_methods(["GET", "DELETE"])
def object_preset(request, campaign_id, preset_id):
    return response(request, campaign_id, lambda: builder_presets.detail(campaign_id, request.user.pk, preset_id)
                    if request.method == "GET" else builder_presets.remove(campaign_id, request.user.pk, preset_id))


@require_GET
def page(request, campaign_id):
    if not request.user.is_authenticated:
        return navigate(request, "/login")
    try:
        who = member(campaign_id, request.user.pk)
        services.manage(who)
        target = services.folder(request.GET.get("folder"), who)
    except (services.MapError, JournalError):
        raise Http404 from None

    context = {
        "campaign": who.campaign,
        "folder": target,
        "back_url": reverse("table:workspace", args=[campaign_id]),
        "owner": True,
        "member_role": who.role,
        **template_context(request),
    }
    response = render(
        request, "gravewright_maps/builder.html", context, using="jinja2"
    )
    response["Cache-Control"] = "private, no-store"
    return response


def response(request, campaign_id, operation):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required.", "code": "forbidden"}, status=403)
    try:
        result = operation()
        result = JsonResponse(result)
        result["Cache-Control"] = "private, no-store"
        return result
    except (services.MapError, JournalError) as error:
        code = getattr(error, "code", "invalid_input")
        status = {"conflict": 409, "forbidden": 403, "not_a_member": 404, "not_found": 404}.get(code, 400)
        return JsonResponse({"error": str(error), "code": code}, status=status)


def body(request):
    if len(request.body) > builder_services.MAX_DOCUMENT_BYTES + 4096:
        raise services.MapError("The map project is too large.")
    try:
        return json.loads(request.body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise services.MapError("Invalid map project command.") from None


@require_GET
def state(request, campaign_id):
    return response(request, campaign_id, lambda: builder_services.catalog(campaign_id, request.user.pk))


@require_http_methods(["GET", "POST"])
def document(request, campaign_id, project_id):
    def operation():
        if request.method == "GET":
            return builder_services.detail(campaign_id, request.user.pk, project_id)
        return builder_services.save(campaign_id, request.user.pk, project_id, body(request))

    return response(request, campaign_id, operation)


@require_POST
def generate(request, campaign_id, project_id):
    return response(request, campaign_id, lambda: builder_services.generate(
        campaign_id, request.user.pk, project_id, body(request)))


@require_POST
def update(request, campaign_id, project_id):
    return response(request, campaign_id, lambda: builder_services.update(
        campaign_id, request.user.pk, project_id, body(request)))


@require_POST
def sync(request, campaign_id, project_id):
    return response(request, campaign_id, lambda: builder_services.sync(
        campaign_id, request.user.pk, project_id, body(request)))


@require_POST
def adopt(request, campaign_id, scene_id):
    from .builder_import import adopt as adopt_scene
    return response(request, campaign_id, lambda: adopt_scene(
        campaign_id, request.user.pk, scene_id, body(request)))


@require_GET
def templates(request, campaign_id):
    return response(request, campaign_id, lambda: blueprint_templates.catalog(campaign_id, request.user.pk))


@require_http_methods(["GET", "POST", "DELETE"])
def template(request, campaign_id, template_id):
    def operation():
        if request.method == "GET":
            return blueprint_templates.detail(campaign_id, request.user.pk, template_id)
        return blueprint_templates.mutate(campaign_id, request.user.pk, template_id, body(request),
                                         delete=request.method == "DELETE")
    return response(request, campaign_id, operation)
