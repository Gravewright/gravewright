"""Local configuration: process variables take precedence over the project .env."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


def load_environment(root=BASE_DIR):
    """Load optional .env defaults without expanding secrets or replacing exports."""
    load_dotenv(root / '.env', override=False, interpolate=False)


def env_bool(name, default=False):
    """Parse explicit boolean spellings; fail startup rather than accept a typo."""
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if value in {'0', 'false', 'no', 'n', 'off'}:
        return False
    raise ValueError(f'{name} must be a boolean.')


def env_path(name, default):
    """Expand ~ and resolve relative paths against BASE_DIR, not the shell cwd."""
    path = Path(os.environ.get(name, '').strip() or default).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def public_origin():
    """Return a normalized origin and Django host, rejecting paths and credentials.

    An empty origin is valid for local HTTP development. Accessing parsed.port
    also rejects malformed or out-of-range ports before serving any requests.
    """
    value = os.environ.get('GRAVEWRIGHT_PUBLIC_ORIGIN', '').strip()
    if not value:
        return '', ''
    # urlsplit strips some controls; reject them before they can change the URL.
    if (any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
            or '?' in value or '#' in value):
        raise ValueError('GRAVEWRIGHT_PUBLIC_ORIGIN must be an HTTP(S) origin without a path.')
    parsed = urlsplit(value)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
            or parsed.path or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None
            or parsed.netloc.endswith(':')):
        raise ValueError('GRAVEWRIGHT_PUBLIC_ORIGIN must be an HTTP(S) origin without a path.')
    # Validate even a port which Django would otherwise never inspect at startup.
    if parsed.port == 0:
        raise ValueError('GRAVEWRIGHT_PUBLIC_ORIGIN has an invalid port.')
    host = parsed.hostname
    host = f'[{host}]' if ':' in host else host
    # Scheme/host casing must not change cookie security or CSRF origin policy.
    origin = f'{parsed.scheme}://{host}'
    if parsed.port is not None:
        origin += f':{parsed.port}'
    return origin, host
