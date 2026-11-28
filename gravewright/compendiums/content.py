"""Bounded, declarative document collections supplied by installed packages.

A system package supplies collections for its own document types. A compendium
module supplies collections either for one required system or, without that
requirement, only system-independent journal packs.

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
MAX_FOLDER_DEPTH = 4
SYSTEM_KINDS = {'actor_pack', 'item_pack', 'spell_pack'}
# Journals belong to the host, so any provider may supply them.
SHARED_KINDS = {'journal_pack'}
MODULE_KINDS = SYSTEM_KINDS | SHARED_KINDS
DOCUMENT_TYPE = re.compile(r'[a-z][a-z0-9_-]{0,79}')
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


def folder_path(value):
    """Return the directory folders a collection's packs appear under.

    ``folder`` is optional display metadata: a list of nested folder names,
    outermost first. Collections without it stay at the directory's top level.
    """
    folder = value.get('folder')
    if folder is None:
        return []
    if (not isinstance(folder, list) or not 1 <= len(folder) <= MAX_FOLDER_DEPTH
            or not all(_text(name) for name in folder)):
        raise ValueError('Invalid compendium folder.')
    return [name.strip() for name in folder]


def requirement(manifest):
    """Return ``(system_id, version_range)`` required by a compendium module, or None.

    System packages provide their own document types and never declare one.
    """
    required = manifest.get('content', {}).get('requiresSystem')
    if required is None:
        return None
    return required['id'], required.get('version')


def _journal_entry(entry):
    from gravewright.journals.data import JOURNAL_TYPES
    if 'systemId' in entry or entry.get('type', 'diary') not in JOURNAL_TYPES:
        raise ValueError('Journal entries use a journal type and belong to no system.')
    if not isinstance(entry.get('data', {}), dict):
        raise ValueError('Invalid journal entry data.')
    for field in ('content', 'content_markdown'):
        if field in entry and not isinstance(entry[field], str):
            raise ValueError('Invalid journal entry content.')


def validate_collection(value, system_id, actor_types, item_types):
    """Validate one collection against its provider's registered document types.

    ``system_id`` is the system whose actors and items the collection may hold;
    None allows only system-independent packs. ``actor_types``/``item_types`` of
    None accept any well-formed type ID: a compendium module is checked against
    its required system's actual types when a table activates or reads it.
    """
    _json(value)
    if not isinstance(value, dict) or not _text(value.get('name')):
        raise ValueError('A compendium collection requires a name.')
    folder_path(value)
    packs = value.get('packs')
    if not isinstance(packs, list) or not 1 <= len(packs) <= MAX_PACKS:
        raise ValueError('Invalid compendium pack count.')
    kinds = MODULE_KINDS if system_id is not None else SHARED_KINDS
    pack_ids, count = set(), 0
    for pack in packs:
        if not isinstance(pack, dict) or pack.get('type') not in MODULE_KINDS:
            raise ValueError('Unsupported installed compendium kind.')
        if pack['type'] not in kinds:
            raise ValueError('Actor, item and spell packs require a system.')
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
            if not _text(entry.get('name')):
                raise ValueError('Unregistered compendium document type or invalid name.')
            if pack['type'] in SHARED_KINDS:
                _journal_entry(entry)
            else:
                kind = entry.get('type')
                if (not isinstance(kind, str) or not DOCUMENT_TYPE.fullmatch(kind)
                        or (types is not None and kind not in types)):
                    raise ValueError('Unregistered compendium document type or invalid name.')
                if entry.get('systemId') != system_id or not isinstance(entry.get('data'), dict):
                    raise ValueError('Compendium documents must belong to their provider system.')
            if len(json.dumps(entry, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_ENTRY_BYTES:
                raise ValueError('Compendium entry quota exceeded.')
    return value
