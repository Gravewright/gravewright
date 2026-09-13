"""ASGI cancellation must propagate without wrapping downstream views in threads."""
import asyncio
from types import ModuleType
from asgiref.testing import ApplicationCommunicator
from asgiref.sync import iscoroutinefunction
from django.core.handlers.asgi import ASGIHandler
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory
from django.urls import path
from gravewright.accounts.middleware import AuthSecurityMiddleware
from gravewright.campaigns.streamer import StreamerMiddleware


class MiddlewareAsyncTests(SimpleTestCase):
    async def test_asgi_disconnect_cancels_view_through_full_middleware_stack(self):
        entered = asyncio.Event()
        cleaned = asyncio.Event()

        async def view(request):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        loop = asyncio.get_running_loop()
        errors = []
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        try:
            urlconf = ModuleType('cancel_test_urls')
            urlconf.urlpatterns = [path('cancel-test', view)]
            with self.settings(ROOT_URLCONF=urlconf):
                connection = ApplicationCommunicator(ASGIHandler(), {
                    'type': 'http', 'http_version': '1.1', 'method': 'GET',
                    'path': '/cancel-test', 'query_string': b'',
                    'headers': [(b'host', b'testserver')], 'scheme': 'http',
                    'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
                })
                await connection.send_input({'type': 'http.request', 'body': b'', 'more_body': False})
                await asyncio.wait_for(entered.wait(), 2)
                await connection.send_input({'type': 'http.disconnect'})
                await connection.wait(timeout=2)
                self.assertTrue(cleaned.is_set())
                await asyncio.sleep(0)
                self.assertEqual(errors, [])
        finally:
            loop.set_exception_handler(previous)

    async def test_cancelled_downstream_request_keeps_native_async_chain(self):
        entered = asyncio.Event()
        cleaned = asyncio.Event()
        async def downstream(request):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        request = RequestFactory().get('/api/example')
        request.user = AnonymousUser()
        chain = AuthSecurityMiddleware(StreamerMiddleware(downstream))
        self.assertTrue(iscoroutinefunction(chain))
        self.assertTrue(iscoroutinefunction(chain.get_response))
        loop = asyncio.get_running_loop()
        errors = []
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        try:
            task = asyncio.create_task(chain(request))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(cleaned.is_set())
            await asyncio.sleep(0)
            self.assertEqual(errors, [])
        finally:
            loop.set_exception_handler(previous)

    async def test_async_request_retains_body_limit_and_security_headers(self):
        calls = []
        async def downstream(request):
            calls.append(request.path)
            return HttpResponse('ok')
        chain = AuthSecurityMiddleware(downstream)
        response = await chain(RequestFactory().post('/api/auth/login', data='x'*16385, content_type='application/json'))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(calls, [])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", response['Content-Security-Policy'])
        response = await chain(RequestFactory().get('/login'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ['/login'])

    def test_favicon_route_exists(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/static/gravewright_web/favicon.svg')
