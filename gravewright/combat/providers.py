"""Trusted system callbacks; the host supplies lifecycle, never game rules.

Server extensions register from AppConfig.ready(). Browser manifests may require
a provider, but cannot import code or select another system's implementation.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Provider:
    prepare_initiative: Callable | None = None
    advance_effects: Callable | None = None


_providers = {}


def register(system_id, *, prepare_initiative=None, advance_effects=None):
    if not isinstance(system_id, str) or not system_id.strip():
        raise ValueError('A system identity is required.')
    if any(callback is not None and not callable(callback)
           for callback in (prepare_initiative, advance_effects)):
        raise ValueError('System callbacks must be callable.')
    provider = Provider(prepare_initiative, advance_effects)
    current = _providers.get(system_id)
    if current is not None and current != provider:
        raise ValueError('A combat provider is already registered for this system.')
    _providers[system_id] = provider
    return provider


def get(system_id):
    return _providers.get(system_id)
