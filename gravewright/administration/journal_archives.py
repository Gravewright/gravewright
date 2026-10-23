"""Portable journal links keep authored text exact and omitted targets inert."""

from copy import deepcopy
import re
from uuid import uuid4

from django.apps import apps

from gravewright.accounts.services import AuthError
from gravewright.journals.data import SECTION_LIMIT, validate_diary_structure
from gravewright.maps.services import MapError
from gravewright.table.resource_links import validate_reference

from .resource_archives import remap_reference

LABELS = {'gravewright_journals.journal', 'gravewright_journals.revision'}
LEGACY_MODELS = {'actor': 'gravewright_actors.actor', 'item': 'gravewright_items.item',
                 'journal': 'gravewright_journals.journal', 'scene': 'gravewright_maps.scene'}


def references(value):
    """Walk inline link nodes without interpreting authored text or URLs."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if item.get('type') == 'gwResourceLink':
                yield item
            pending.extend(child for child in item.values() if isinstance(child, (dict, list)))
        elif isinstance(item, list):
            pending.extend(child for child in item if isinstance(child, (dict, list)))


def validate_record(record):
    if record['model'] not in LABELS:
        return
    fields = record['fields']
    data = fields.get('data')
    if fields.get('type') == 'diary':
        try:
            validate_diary_structure(data)
            sections = data.get('sections', [])
            # Normalization must not truncate imported pages or collapse their
            # local identities on the next save. Legacy IDs remain literal.
            identifiers = [str(page.get('id') or '').strip()[:40] for page in sections if isinstance(page, dict)]
            present = [identifier for identifier in identifiers if identifier]
            if len(sections) > SECTION_LIMIT or len(present) != len(set(present)):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise AuthError('invalid_archive') from None
    for index, node in enumerate(references(record['fields'].get('data'))):
        try:
            if index >= 512 or not isinstance(node.get('attrs'), dict) or set(node['attrs']) != {'reference'}:
                raise ValueError()
            validate_reference(node['attrs']['reference'])
        except (MapError, ValueError, TypeError, KeyError):
            raise AuthError('invalid_archive') from None


def import_document(value, model_ids, inert, paths, identifiers, *, snapshot):
    def binding(label, source):
        if not source:
            return source
        key = (label, str(source))
        target = model_ids.get(key) or inert.setdefault(key, str(source) if snapshot else str(uuid4()))
        return str(target)

    def link_url(value):
        if value in paths:
            return paths[value]
        if not value.startswith('/game/'):
            return value
        value = re.sub(r'^/game/([0-9a-f-]{36})(?=[/?#]|$)',
            lambda match: '/game/' + identifiers.get(match[1], match[1]), value)
        value = re.sub(r'^/game/journal/asset/([0-9a-f-]{36})(?=[/?#]|$)',
            lambda match: '/game/journal/asset/' + binding('gravewright_journals.asset', match[1]), value)
        return re.sub(r'([?&]document=)(actor|item|journal|scene):([0-9a-f-]{36})(?=[&#]|$)',
            lambda match: match[1] + match[2] + ':' + binding(LEGACY_MODELS[match[2]], match[3]), value)

    def document(item):
        if isinstance(item, dict):
            if item.get('type') == 'gwResourceLink':
                return {'type': 'gwResourceLink', 'attrs': {'reference': remap_reference(
                    item['attrs']['reference'], model_ids, inert, identifiers, snapshot=snapshot)}}
            result = {}
            for key, child in item.items():
                if key in ('assetId', 'asset_id') and isinstance(child, str):
                    result[key] = binding('gravewright_journals.asset', child)
                elif key in ('assignees', 'prerequisites') and isinstance(child, list):
                    label = 'gravewright_actors.actor' if key == 'assignees' else 'gravewright_journals.journal'
                    result[key] = [binding(label, source) for source in child]
                elif key in ('href', 'src') and isinstance(child, str):
                    result[key] = link_url(child)
                else:
                    result[key] = document(child)
            return result
        if isinstance(item, list):
            return [document(child) for child in item]
        return deepcopy(item)

    return document(value)


def import_documents(payload, model_ids, inert, paths, identifiers, *, snapshot):
    """Wait until numeric keys exist; all writes remain in the import transaction."""
    for record in payload['records']:
        if record['model'] not in LABELS:
            continue
        value = import_document(record['fields']['data'], model_ids, inert, paths, identifiers, snapshot=snapshot)
        model = apps.get_model(record['model'])
        model.objects.filter(pk=model_ids[(record['model'], str(record['pk']))]).update(data=value)
