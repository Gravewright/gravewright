"""Bundled system modules register their own data and sheet implementation."""

from copy import deepcopy
import json

from gravewright.maps.services import MapError

DEFAULT_SYSTEM = 'gravewright-pdf-system'
_bundled = {}


def register(system_id, *, descriptor, sheet, normalize, validate=None, remove_asset=None, combat=None):
    _bundled[system_id] = dict(descriptor=descriptor, sheet=sheet, normalize=normalize, validate=validate, remove_asset=remove_asset, combat=combat)


def bundled(system_id):
    return _bundled.get(system_id or DEFAULT_SYSTEM)


def sheet_provider(system_id):
    module = bundled(system_id)
    return deepcopy(module['sheet']) if module else None


def remove_asset_references(system_id, campaign_id, asset):
    module = bundled(system_id)
    if module and module['remove_asset']:
        module['remove_asset'](campaign_id, asset)


def normalize_actor(system_id, raw, previous=None, gm=True, *, campaign_id=None):
    module = bundled(system_id)
    if module:
        result = module['normalize'](raw, previous, gm)
        if module['validate'] and campaign_id is not None:
            module['validate'](result, campaign_id)
        return result
    # External systems own their document shape. The host only bounds JSON;
    # it never injects another system's fields or presentation settings.
    try:
        if not isinstance(raw, dict) or len(json.dumps(raw, allow_nan=False)) > 500_000:
            raise ValueError

        def check(value, depth=0):
            if depth > 64:
                raise ValueError
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str) or key in {'__proto__', 'constructor', 'prototype'}:
                        raise ValueError
                    check(item, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    check(item, depth + 1)
        check(raw)
    except (ValueError, TypeError, RecursionError):
        raise MapError('Invalid character sheet.') from None
    # Active effects remain GM controlled in every system.
    if not gm and 'effects' in raw and raw['effects'] != (previous or {}).get('effects', []):
        raise MapError('Only the GM can edit active effects.')
    if not gm:
        def token_size(value):
            token = value.get('token')
            return token.get('size', 1) if isinstance(token, dict) else 1
        if token_size(raw) != token_size(previous or {}):
            raise MapError('Only the GM can change token size.', 'forbidden')
    result = deepcopy(raw)
    if not gm and 'effects' not in raw and 'effects' in (previous or {}):
        result['effects'] = deepcopy(previous['effects'])
    if 'effects' in result and (not isinstance(result['effects'], list) or len(result['effects']) > 128 or any(not isinstance(effect, dict) for effect in result['effects'])):
        raise MapError('Invalid active effects.')
    return result
