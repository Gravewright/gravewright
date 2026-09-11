"""Public extension interface. GPL-3.0-only with LICENSE-EXCEPTION.

Import domain modules explicitly, e.g. ``from api import actors, resources``.
Django must be initialized before importing services. No apps are registered here.
"""
from .context import Context

API_VERSION = '1.0'
__all__ = ['API_VERSION', 'Context']
