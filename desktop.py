"""Gravewright desktop launcher.

Runs the Litestar/uvicorn server *in-process* (a background thread) and shows it
inside a native window via pywebview. This is the entry point used for the
PyInstaller one-dir build, so a non-technical user just double-clicks the exe and
gets a real app window — no terminal, no Python, no `uv` required.

Why in-process instead of `grave run`: the CLI launches the server with
``subprocess.run([sys.executable, "-m", "uvicorn", "main:app"])`` which is broken
in a frozen build (``sys.executable`` is the exe itself, not a Python interpreter,
and ``main.py`` is not shipped as a loose source file).
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path


def _writable_base_dir() -> Path:
    """Folder where the SQLite DB, packages and uploads live.

    Frozen: a ``GravewrightData`` folder next to the executable so the install
    stays self-contained and portable. From source: the project root (unchanged
    dev behaviour).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent / "GravewrightData"
    else:
        base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_user_env() -> Path | None:
    """Let end users configure the frozen app with a ``.env`` next to the exe.

    When frozen, the app's ``PROJECT_ROOT`` resolves inside ``_internal/`` — not a
    place a user should edit, and wiped on every update. So we load a ``.env``
    sitting beside the executable first. Under the app's "first write wins"
    semantics, values loaded here take precedence over the bundled defaults and
    over our own ``setdefault`` calls below.
    """
    if not getattr(sys, "frozen", False):
        return None
    env_path = Path(sys.executable).resolve().parent / ".env"
    if not env_path.exists():
        return None
    from app.helpers.env import _apply_file

    _apply_file(env_path)
    return env_path


def _configure_environment(host: str, port: int) -> None:
    """Point the app at writable locations. Must run before importing config."""
    _load_user_env()

    base = _writable_base_dir()
    storage = base / "storage"
    storage.mkdir(parents=True, exist_ok=True)

    # config reads these at import time, so set paths before importing main.
    os.environ.setdefault("GRAVEWRIGHT_DATA_DIR", str(base / "data"))
    os.environ.setdefault(
        "DATABASE_URL", f"sqlite:///{(storage / 'gravewright.sqlite3').resolve()}"
    )
    # The allowed-hosts middleware full-matches the Host header (incl. port); with
    # an ephemeral loopback port a fixed host never matches. The window only ever
    # talks to 127.0.0.1, so trust any host.
    os.environ["APP_ENV"] = "development"
    os.environ["ALLOWED_HOSTS"] = "*"
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    # The realtime WebSocket guard checks the handshake Origin. It would otherwise
    # be derived from ALLOWED_HOSTS=* as "http://*", which never matches an origin
    # that carries a port -> the chat/board socket is rejected with 403. Pin the
    # exact origins this window uses so authenticated sockets connect.
    local_origins = (f"http://{host}:{port}", f"http://localhost:{port}")
    configured_origins = tuple(
        origin.strip()
        for origin in os.environ.get("WS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    os.environ["WS_ALLOWED_ORIGINS"] = ",".join(
        dict.fromkeys((*local_origins, *configured_origins))
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# Evergreen WebView2 Runtime registration (same GUID on every machine).
_WEBVIEW2_CLIENT = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
_WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"


def _webview2_installed() -> bool:
    """True if the WebView2 runtime is registered for this machine or user.

    The native window backend on Windows is WebView2; without the runtime the
    window simply fails to appear. We probe the EdgeUpdate registry keys it
    writes (per-machine 64/32-bit, then per-user).
    """
    import winreg

    candidates = (
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT}"),
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT}"),
    )
    for root, subkey in candidates:
        try:
            with winreg.OpenKey(root, subkey) as key:
                version, _ = winreg.QueryValueEx(key, "pv")
        except OSError:
            continue
        if version and version != "0.0.0.0":
            return True
    return False


def _require_webview2() -> bool:
    """On frozen Windows builds, ensure WebView2 is present before showing a window.

    If it is missing, tell the user in a native dialog, open the download page,
    and return False so the launcher exits cleanly instead of dying silently.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return True
    if _webview2_installed():
        return True

    import ctypes
    import webbrowser

    message = (
        "Gravewright needs the Microsoft WebView2 Runtime to open its window.\n\n"
        "It is missing on this computer. We'll open the download page now — "
        "install it (it's free, from Microsoft), then start Gravewright again.\n\n"
        f"Link: {_WEBVIEW2_DOWNLOAD_URL}"
    )
    # MB_OK | MB_ICONWARNING
    ctypes.windll.user32.MessageBoxW(0, message, "Gravewright", 0x30)
    try:
        webbrowser.open(_WEBVIEW2_DOWNLOAD_URL)
    except Exception:  # noqa: BLE001 - best effort, dialog already informed the user
        pass
    return False


def main() -> int:
    if not _require_webview2():
        return 1

    # Pick the port before importing config: WS_ALLOWED_ORIGINS must contain the
    # exact origin (incl. this port), and config reads it once at import time.
    host = "127.0.0.1"
    port = _free_port()
    _configure_environment(host, port)

    # Imported after the environment is configured so config picks up our paths.
    import uvicorn
    import webview

    from app.persistence.database import initialize_database
    from main import app

    # Create any missing tables on first launch.
    initialize_database()

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            # Avoid Uvicorn's dynamic protocol selection in a frozen build.
            # This implementation is bundled with the pinned websockets package.
            ws="websockets-sansio",
        )
    )
    # Signal handlers can only be installed on the main thread; the server runs on
    # a worker thread here, so make this a no-op to avoid a ValueError on startup.
    server.install_signal_handlers = lambda: None

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for uvicorn to finish startup before pointing the window at it.
    deadline = time.time() + 30
    while not server.started and time.time() < deadline:
        if not thread.is_alive():
            print("Server thread exited during startup.", file=sys.stderr)
            return 1
        time.sleep(0.1)
    if not server.started:
        print("Server did not start within 30s.", file=sys.stderr)
        return 1

    webview.create_window(
        "Gravewright",
        f"http://{host}:{port}/",
        width=1280,
        height=800,
        min_size=(900, 600),
    )
    webview.start()  # blocks until the window is closed

    # Window closed -> stop the server cleanly.
    server.should_exit = True
    thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
