"""Canonical inline references and recipient-specific, non-disclosing displays."""

from copy import deepcopy
import json

from django.utils.crypto import salted_hmac

MAX_LINKS = 512
NODE_TYPE = 'gwResourceLink'


def nodes(value):
    """Walk a normalized journal or projection without interpreting authored text."""
    if isinstance(value, dict):
        if value.get('type') == NODE_TYPE:
            yield value
        else:
            for child in value.values():
                yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def canonical(value):
    from gravewright.table.resource_links import validate_reference
    from gravewright.maps.services import MapError
    from .services import JournalError
    try:
        return validate_reference(value)
    except MapError:
        raise JournalError('Invalid resource reference.') from None


def key(journal, reference):
    value = str(journal.pk) + ':' + json.dumps(reference, sort_keys=True, separators=(',', ':'))
    return salted_hmac('gravewright.journal.resource.v1', value, algorithm='sha256').hexdigest()


def project(value, journal, who, resolver=None):
    """Run only after page/block filtering; never deliver an inaccessible identity."""
    from gravewright.table.resource_links import Resolver
    from .services import JournalError
    result = deepcopy(value)
    if not any(nodes(result)):
        return result
    resolver = resolver() if callable(resolver) else resolver or Resolver(who)
    for node in nodes(result):
        try:
            ref = canonical(node.get('attrs', {}).get('reference'))
        except JournalError:
            # Older imported data cannot turn a corrupt reference into an ID leak.
            node['attrs'] = {'reference': {'unavailable': True}}
            continue
        display = resolver.resolve(ref)
        node['attrs'] = {'reference': {**(display or {'unavailable': True}), 'key': key(journal, ref)}}
    return result


def clean(value, journal, who, *, trusted=False):
    """Accept readable new refs or references already present in visible content.

    Opaque placeholders are recoverable only within this journal's currently
    authorized projection. Restoring a server-owned history row may retain
    missing targets; it cannot manufacture new references from user input.
    """
    from gravewright.table.resource_links import Resolver
    from .services import JournalError, projection
    incoming = list(nodes(value))
    if len(incoming) > MAX_LINKS:
        raise JournalError('Use up to 512 resource references per document.')
    if not incoming:
        return value
    allowed = {}
    for node in nodes(projection(journal, who, _resolve_links=False)):
        try:
            ref = canonical(node.get('attrs', {}).get('reference'))
        except JournalError:
            continue
        allowed[key(journal, ref)] = ref
    resolver = Resolver(who)
    for node in incoming:
        raw = node.get('attrs', {}).get('reference')
        if isinstance(raw, dict) and raw.get('unavailable') is True:
            if set(raw) != {'unavailable', 'key'} or not isinstance(raw.get('key'), str) or raw['key'] not in allowed:
                raise JournalError('Invalid resource reference.')
            ref = allowed[raw['key']]
        else:
            # Live projection metadata is display-only, never persisted. Reject
            # arbitrary fields rather than treating hostile markup as metadata.
            display_fields = {'kind', 'id', 'pageId', 'key', 'label', 'labelKey', 'description',
                              'descriptionKey', 'sceneId', 'ownerReference'}
            if not isinstance(raw, dict) or set(raw) - display_fields:
                raise JournalError('Invalid resource reference.')
            ref = canonical({name: raw[name] for name in ('kind', 'id', 'pageId') if name in raw})
            if not trusted and key(journal, ref) not in allowed and resolver.resolve(ref) is None:
                raise JournalError('Resource not found or access denied.', 'not_found')
        node['attrs'] = {'reference': deepcopy(ref)}
    return value
