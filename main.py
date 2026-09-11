"""Start the local ASGI server with the host and port from .env."""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    from django.core.management import execute_from_command_line

    host = settings.GRAVEWRIGHT_HOST
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    execute_from_command_line([
        sys.argv[0], 'runserver', f'{host}:{settings.GRAVEWRIGHT_PORT}', *sys.argv[1:],
    ])


if __name__ == '__main__':
    main()
