"""Maintenance gate and private readiness probe for the update supervisor."""
import json
import os
from pathlib import Path
import secrets
if os.environ.get('GRAVEWRIGHT_RUNNER_DATA'):
    from config.runner_asgi import application as project_application
else:
    from config.asgi import application as project_application
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.db import connection
from asgiref.sync import sync_to_async


@sync_to_async
def database_ready():
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        return cursor.fetchone()[0] == 1


class ManagedApplication:
    def __init__(self):
        self.application = project_application if os.environ.get('GRAVEWRIGHT_RUNNER_DATA') else ASGIStaticFilesHandler(project_application)

    async def __call__(self, scope, receive, send):
        state = os.environ.get('GRAVEWRIGHT_MANAGED_STATE')
        token = os.environ.get('GRAVEWRIGHT_MANAGED_TOKEN', '')
        if scope['type'] == 'http' and scope.get('path') == '/__gravewright_update_health':
            headers = dict(scope.get('headers', []))
            supplied = headers.get(b'x-gravewright-update', b'').decode('ascii', errors='ignore')
            allowed = bool(token) and secrets.compare_digest(supplied, token)
            healthy = allowed and await database_ready()
            await send({'type': 'http.response.start', 'status': 200 if healthy else 403,
                        'headers': [(b'content-type', b'application/json'), (b'cache-control', b'no-store')]})
            await send({'type': 'http.response.body', 'body': json.dumps({'token': token} if healthy else {}).encode()})
            return
        if state and (Path(state) / 'maintenance').exists():
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1012})
            else:
                await send({'type': 'http.response.start', 'status': 503,
                            'headers': [(b'content-type', b'text/plain'), (b'retry-after', b'5'), (b'cache-control', b'no-store')]})
                await send({'type': 'http.response.body', 'body': b'Gravewright is updating. Please retry shortly.'})
            return
        await self.application(scope, receive, send)


application = ManagedApplication()
