"""Encounter-scoped clocks and periodic effects on authoritative sheet instances."""
from copy import deepcopy

from django.db.models import F

from gravewright.actors.models import Actor
from gravewright.tokens.models import Token
from .providers import get as combat_provider


def _instances(encounter):
    """A linked actor is one document; each independent token is its own document."""
    entries = encounter.combatants[:64]
    token_ids = [entry['tokenId'] for entry in entries if entry.get('tokenId')]
    tokens = {str(token.pk): token for token in Token.objects.filter(
        scene=encounter.scene, pk__in=token_ids,
        actor__campaign_id=encounter.scene.campaign_id,
    ).select_related('actor')}
    actor_ids = [entry['actorId'] for entry in entries if not entry.get('tokenId') and entry.get('actorId')]
    actors = {str(actor.pk): actor for actor in Actor.objects.filter(
        campaign_id=encounter.scene.campaign_id, pk__in=actor_ids,
    )}
    documents = {}
    for entry in entries:
        token = tokens.get(str(entry.get('tokenId', '')))
        actor = token.actor if token else actors.get(str(entry.get('actorId', '')))
        if actor is None:
            continue
        independent = token is not None and not token.linked
        key = ('token', str(token.pk)) if independent else ('actor', str(actor.pk))
        document = documents.setdefault(key, {
            'key': key,
            'actor': actor, 'token': token if independent else None,
            'data': token.snapshot if independent else actor.data, 'token_ids': set(),
        })
        if token is not None:
            document['token_ids'].add(str(token.pk))
    return list(documents.values()), tokens


def advance(encounter, phase, entry, *, round_boundary=False, provider=None, periodic=True, ticked=None):
    """Dispatch system-owned rules inside the native command transaction.

    The host resolves participating documents and persists their isolated copies.
    Only the registered system decides what any field, condition or clock means.
    An absent provider leaves sheet JSON unchanged.
    """
    if not encounter.active or phase not in ('start', 'end'):
        return
    from gravewright.campaigns.systems import resolve_system_id
    provider = provider or combat_provider(resolve_system_id(encounter.scene.campaign.system))
    if provider is None or provider.advance_effects is None:
        return
    if not any((candidate.get('tokenId') or candidate.get('actorId')) ==
               (entry.get('tokenId') or entry.get('actorId')) for candidate in encounter.combatants):
        return
    documents, tokens = _instances(encounter)
    token_id = str(entry.get('tokenId') or '')
    event_token = tokens.get(token_id)
    actor_id = str(event_token.actor_id) if event_token else str(entry.get('actorId') or '')
    if token_id and event_token is None:
        return
    if not token_id and not any(document['token'] is None and str(document['actor'].pk) == actor_id
                                for document in documents):
        return
    clock_keys = ticked if ticked is not None else set()
    for document in documents:
        if not isinstance(document['data'], dict):
            continue
        owner_token_id = str(document['token'].pk) if document['token'] is not None else ''
        owner_actor_id = str(document['actor'].pk)
        data = deepcopy(document['data'])
        event = {
            'phase': phase, 'roundBoundary': round_boundary,
            'isCurrent': (owner_token_id == token_id if owner_token_id else
                          owner_actor_id == actor_id and (event_token is None or event_token.linked)),
            'periodic': periodic, 'actorType': document['actor'].type,
            'conditions': deepcopy(event_token.conditions) if event_token else [],
            'tokenId': token_id, 'actorId': actor_id,
            'ownerTokenId': owner_token_id, 'ownerActorId': owner_actor_id,
            'clockKeys': clock_keys, 'documentKey': document['key'],
        }
        if provider.advance_effects(data, event):
            # Reuse the same bounded document contract as a normal sheet save.
            from gravewright.campaigns.systems import normalize_actor
            data = normalize_actor(encounter.scene.campaign.system, data, document['data'],
                                   gm=True, campaign_id=encounter.scene.campaign_id)
            if document['token'] is not None:
                document['token'].snapshot = data
            else:
                document['actor'].data = data
            persist(document['actor'], document['token'])


def persist(actor, token=None):
    if token is not None:
        token.sheet_version += 1
        token.version += 1
        token.save(update_fields=['snapshot', 'sheet_version', 'version'])
        return
    actor.sheet_version += 1
    actor.version += 1
    actor.save(update_fields=['data', 'sheet_version', 'version', 'updated_at'])
    actor.tokens.filter(linked=True).update(version=F('version') + 1)
