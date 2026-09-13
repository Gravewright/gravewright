from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class AuthSecurityMiddleware(MiddlewareMixin):
    """Bound authentication bodies before CSRF middleware parses form data."""

    def process_request(self, request):
        is_api = request.path.startswith('/api/auth/')
        is_auth = is_api or request.path in {'/setup', '/register', '/login', '/logout', '/inside/account'}
        content_length = request.META.get('CONTENT_LENGTH', '')
        declared_size = int(content_length) if content_length.isdecimal() else 0
        oversized = is_auth and request.method == 'POST' and (
            declared_size > 16 * 1024 or len(request.body) > 16 * 1024
        )
        if oversized:
            if is_api:
                response = JsonResponse({'error': 'request_too_large'}, status=413)
            else:
                response = HttpResponse(status=413)
            return response
        return None

    def process_response(self, request, response):
        if not request.path.startswith(('/static/', '/admin/')):
            response['Cache-Control'] = 'no-store'
            # Datastar compiles trusted expressions in data-* attributes.
            response['Content-Security-Policy'] = (
                "default-src 'none'; script-src 'self' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https: http:; "
                "font-src 'self'; media-src 'self' blob:; connect-src 'self'; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'"
            )
        return response
