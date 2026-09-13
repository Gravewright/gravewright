"""Start the local ASGI server with the host and port from .env."""

import os
import sys


def main():
    if os.name == 'nt' and not sys.flags.utf8_mode:
        os.execv(sys.executable, [sys.executable, '-X', 'utf8', *sys.argv])
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    from django.core.management import execute_from_command_line

    if '--dev' not in sys.argv:
        import hashlib
        from pathlib import Path
        from scripts.update_supervisor import Supervisor
        origin = settings.BASE_DIR
        identity = hashlib.sha256(str(origin).encode()).hexdigest()[:16]
        from scripts.process_control import state_home
        state = state_home() / identity
        database = Path(settings.DATABASES['default']['NAME']).resolve()
        media = Path(settings.MEDIA_ROOT).resolve()
        if state.is_relative_to(media) or media == origin or origin.is_relative_to(media):
            raise SystemExit('Update storage and media must be separate from application code.')
        import signal
        def stop_managed(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop_managed)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, stop_managed)
        supervisor = Supervisor(origin, state, database, media, settings.GRAVEWRIGHT_HOST, settings.GRAVEWRIGHT_PORT)
        try:
            supervisor.run()
        except KeyboardInterrupt:
            pass
        return

    sys.argv = [arg for arg in sys.argv if arg not in {'--dev', '--managed'}]
    host = settings.GRAVEWRIGHT_HOST
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    execute_from_command_line([
        sys.argv[0], 'runserver', f'{host}:{settings.GRAVEWRIGHT_PORT}', *sys.argv[1:],
    ])


if __name__ == '__main__':
    main()
