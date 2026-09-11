"""Runner readiness and local static assets, behind normal Django middleware."""

from django.conf import settings
from django.http import JsonResponse
from django.urls import path, re_path
from django.views.decorators.http import require_GET
from django.views.static import serve

from config.urls import urlpatterns as project_urls


@require_GET
def ready(request):
    """Identify this exact process before the launcher opens a browser tab."""
    return JsonResponse({'runner': settings.RUNNER_TOKEN})


urlpatterns = [
    path('__gravewright_runner__/ready', ready),
    re_path(r'^static/(?P<path>.*)$', serve,
            {'document_root': settings.STATIC_ROOT, 'show_indexes': False}),
    *project_urls,
]
