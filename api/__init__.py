"""Public extension interface. GPL-3.0-only with LICENSE-EXCEPTION.

Import domain modules explicitly, e.g. ``from api import actors, resources``.
Django must be initialized before importing services. No apps are registered here.
"""
from .context import Context

API_VERSION = '1.0'
__all__ = ['API_VERSION', 'Context', 'capabilities']


def capabilities():
    """Describe the versioned browser method catalog without accessing user data.

    The catalog documents methods; it never grants a caller permissions. Resolve
    a campaign system's registered operations with ``api.systems.capabilities``.
    """
    import json
    from pathlib import Path
    contract = Path(__file__).resolve().parents[1] / 'gravewright/modules/contracts/frontend.json'
    return {'pythonVersion': API_VERSION, 'browser': json.loads(contract.read_text(encoding='utf-8'))}
