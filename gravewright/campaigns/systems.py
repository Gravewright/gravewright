"""Bundled system modules register their own data and sheet implementation."""

from copy import deepcopy
import json

_bundled = {}
_default_system = ''


def register(system_id, *, descriptor, sheet, normalize, validate=None,
             remove_asset=None, combat=None, default=False, assets=None, templates=None):
    """Register a server provider without assigning rules to the host itself."""
    global _default_system
    _bundled[system_id] = dict(
        descriptor=descriptor, sheet=sheet, normalize=normalize, validate=validate,
        remove_asset=remove_asset, combat=combat, assets=assets, templates=templates,
    )
    if default:
        _default_system = system_id


def default_system_id():
    """Resolve after app ready, including historical campaigns with a blank ID."""
    return _default_system


def resolve_system_id(system_id):
    return system_id or default_system_id()


def bundled(system_id):
    return _bundled.get(resolve_system_id(system_id))


def bundled_descriptors():
    rows = list(_bundled.items())
    rows.sort(key=lambda row: (row[0] != default_system_id(), row[1]['descriptor']['title'].casefold(), row[0]))
    return [deepcopy(provider['descriptor']) for _, provider in rows]


def asset_provider(system_id):
    provider = bundled(system_id)
    return dict(provider['assets']) if provider and provider.get('assets') else None


def asset_provider_for(*, kind=None, content_type=None):
    """Find a registered file validator; storage is not tied to table rules."""
    for provider in _bundled.values():
        assets = provider.get('assets')
        if assets and ((kind is not None and assets['kind'] == kind)
                       or (content_type is not None and assets['content_type'] == content_type)):
            return dict(assets)
    return None


def default_asset_kind():
    provider = asset_provider(default_system_id())
    return provider['kind'] if provider else ''


def asset_content_type(kind):
    if kind in {'portrait', 'token'}:
        return 'image/png'
    for provider in _bundled.values():
        assets = provider.get('assets')
        if assets and assets['kind'] == kind:
            return assets['content_type']
    return 'application/octet-stream'


def actor_templates(system_id, campaign_id):
    provider = bundled(system_id)
    callback = provider.get('templates') if provider else None
    return callback(campaign_id) if callback else []


def sheet_provider(system_id):
    module = bundled(system_id)
    return deepcopy(module['sheet']) if module else None


def remove_asset_references(system_id, campaign_id, asset):
    module = bundled(system_id)
    if not module or not module.get('assets') or module['assets']['kind'] != asset.kind:
        module = next((provider for provider in _bundled.values()
                       if provider.get('assets') and provider['assets']['kind'] == asset.kind), None)
    if module and module['remove_asset']:
        module['remove_asset'](campaign_id, asset)


def normalize_actor(system_id, raw, previous=None, gm=True, *, campaign_id=None):
    from gravewright.maps.services import MapError
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
