from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

_loaded = False


def _apply_file(path: Path) -> None:
    """Set any keys from ``path`` that are not already in the environment.

    "First write wins": real OS environment variables always take precedence, and
    among files the one applied first wins.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _detect_app_env() -> str:
    """Resolve the active environment name to choose the ``.env.<APP_ENV>`` file.

    Honours an explicit ``APP_ENV`` in the OS environment; otherwise peeks the
    base ``.env`` for an ``APP_ENV`` line; defaults to ``development``.
    """
    explicit = os.environ.get("APP_ENV")
    if explicit:
        return explicit

    if ENV_FILE.exists():
        for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("APP_ENV") and "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value

    return "development"


def load_environment() -> None:
    """Load environment variables from ``.env`` then ``.env.<APP_ENV>``.

    Order is ``.env`` first, ``.env.<APP_ENV>`` second. Under "first write wins"
    this means a developer's local ``.env`` overrides the committed
    per-environment file, which in turn supplies the environment's defaults. Real
    OS environment variables always win over both. Runs once per process.
    """
    global _loaded
    if _loaded:
        return

    app_env = _detect_app_env()
    _apply_file(ENV_FILE)
    _apply_file(PROJECT_ROOT / f".env.{app_env}")
    _loaded = True


def load_env_file(path: Path = ENV_FILE) -> None:
    """Backwards-compatible single-file loader (no APP_ENV layering)."""
    _apply_file(path)


def env_str(key: str, default: str = "") -> str:
    load_environment()
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    load_environment()

    value = os.getenv(key)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def env_int(key: str, default: int = 0) -> int:
    load_environment()

    value = os.getenv(key)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default
