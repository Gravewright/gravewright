"""Bounded, declarative document collections supplied by installed systems.

This validator has no Django dependencies so installation can reject malformed
packs before writing an approved archive to disk. It never evaluates expressions.
"""
import json
import math
import re

MAX_COLLECTION_BYTES = 8 * 1024 * 1024
MAX_COLLECTION_ENTRIES = 20000
MAX_PACKS = 64
MAX_ENTRY_BYTES = 256 * 1024
MODULE_KINDS = {'actor_pack', 'item_pack', 'spell_pack'}
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}')


def _json(value, depth=0):
    if depth > 24:
        raise ValueError('Compendium JSON exceeds the nesting limit.')
    if isinstance(value, dict):
        if any(not isinstance(key, str) or key in {'__proto__', 'prototype', 'constructor'} for key in value):
            raise ValueError('Invalid compendium JSON key.')
        for child in value.values():
            _json(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _json(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Compendium numbers must be finite.')
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ValueError('Invalid compendium JSON value.')


def _text(value, limit=120):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def validate_collection(value, system_id, actor_types, item_types):
    """Validate one collection against its provider's registered document types."""
    _json(value)
    if not isinstance(value, dict) or not _text(value.get('name')):
        raise ValueError('A compendium collection requires a name.')
    packs = value.get('packs')
    if not isinstance(packs, list) or not 1 <= len(packs) <= MAX_PACKS:
        raise ValueError('Invalid compendium pack count.')
    pack_ids, count = set(), 0
    for pack in packs:
        if not isinstance(pack, dict) or pack.get('type') not in MODULE_KINDS:
            raise ValueError('Unsupported installed compendium kind.')
        pack_id = pack.get('id')
        if not isinstance(pack_id, str) or not IDENTIFIER.fullmatch(pack_id) or pack_id in pack_ids:
            raise ValueError('Invalid or duplicate compendium pack ID.')
        if not _text(pack.get('label')):
            raise ValueError('A compendium pack requires a label.')
        pack_ids.add(pack_id)
        entries = pack.get('entries')
        if not isinstance(entries, list):
            raise ValueError('Compendium entries must be an array.')
        count += len(entries)
        if count > MAX_COLLECTION_ENTRIES:
            raise ValueError('Compendium entry quota exceeded.')
        entry_ids = set()
        types = actor_types if pack['type'] == 'actor_pack' else item_types
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError('Invalid compendium entry.')
            entry_id = entry.get('id')
            if not isinstance(entry_id, str) or not IDENTIFIER.fullmatch(entry_id) or entry_id in entry_ids:
                raise ValueError('Invalid or duplicate compendium entry ID.')
            entry_ids.add(entry_id)
            if not _text(entry.get('name')) or entry.get('type') not in types:
                raise ValueError('Unregistered compendium document type or invalid name.')
            if entry.get('systemId') != system_id or not isinstance(entry.get('data'), dict):
                raise ValueError('Compendium documents must belong to their provider system.')
            if len(json.dumps(entry, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_ENTRY_BYTES:
                raise ValueError('Compendium entry quota exceeded.')
    return value
