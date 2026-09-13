"""Server child with graceful console-stop handling on Windows, macOS and Linux."""
import os
from pathlib import Path
import signal
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    from daphne.server import Server
    from twisted.internet import reactor
    from config.managed_asgi import application
    from scripts.gravewright_runner import finish_asyncio
    host=os.environ.get('GRAVEWRIGHT_HOST','127.0.0.1')
    port=os.environ.get('GRAVEWRIGHT_PORT','3000')
    endpoint=f'tcp:port={port}:interface={host.replace(":", r"\:")}'
    server=Server(application,endpoints=[endpoint],signal_handlers=True,verbosity=1)
    if hasattr(signal,'SIGBREAK'):
        signal.signal(signal.SIGBREAK,lambda *_:reactor.callFromThread(server.stop))
    try:server.run()
    finally:finish_asyncio(reactor._asyncioEventloop)


if __name__=='__main__':main()
