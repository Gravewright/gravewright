"""Navigation responses shared by ordinary HTML requests and Datastar updates."""

import json
from html import escape

from datastar_py.django import DatastarResponse, ServerSentEventGenerator as SSE
from django.shortcuts import redirect


def navigate(request, location):
    """Navigate to an application-owned URL without requiring inline scripts."""
    if request.headers.get('Datastar-Request') == 'true':
        expression = escape(f'window.location.assign({json.dumps(location)})', quote=True)
        return DatastarResponse(SSE.patch_elements(f'<div id="app" data-init="{expression}"></div>'))
    return redirect(location)
