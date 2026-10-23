"""Portable mind maps remap typed links without rewriting authored graph text."""

from copy import deepcopy
from uuid import UUID

from gravewright.accounts.services import AuthError
from gravewright.maps.services import MapError, title
from gravewright.table.mindmaps import MAX_MAPS, validate_document
from .resource_archives import remap_reference

LABEL = 'gravewright_table.mindmap'


def validate_record(record):
    if record['model'] != LABEL:
        return
    fields = record['fields']
    try:
        UUID(str(record['pk']))
        UUID(fields['campaign'])
        if fields['scene'] is not None:
            UUID(fields['scene'])
        title(fields['name'])
        if fields['visibility'] not in ('gm', 'players'):
            raise ValueError()
        editors = fields['editor_ids']
        if not isinstance(editors, list) or len(editors) > 128 or len(set(editors)) != len(editors):
            raise ValueError()
        for value in editors:
            if not isinstance(value, str):
                raise ValueError()
            UUID(value)
        if type(fields['version']) is not int or not 1 <= fields['version'] <= 2**31 - 1:
            raise ValueError()
        validate_document(fields['document'])
    except (MapError, ValueError, TypeError, KeyError, AttributeError):
        raise AuthError('invalid_archive') from None


def validate_limit(records, existing=0):
    if existing + sum(row['model'] == LABEL for row in records) > MAX_MAPS:
        raise AuthError('invalid_archive')


def export_record(record, *, snapshot):
    if record['model'] == LABEL and not snapshot:
        record['fields']['editor_ids'] = []


def import_record(record, model_ids, inert, identifiers, *, snapshot):
    fields = deepcopy(record['fields'])
    fields['document'] = validate_document(fields['document'])
    fields['editor_ids'] = fields['editor_ids'] if snapshot else []

    for node in fields['document']['nodes']:
        node['links'] = [remap_reference(ref, model_ids, inert, identifiers, snapshot=snapshot)
                         for ref in node['links']]
    return fields
