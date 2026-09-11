"""Original round-effect semantics persisted through Django actor documents."""
from typing import Any
from django.db.models import F
from gravewright.actors.models import Actor
from gravewright.tokens.models import Token
from .active_effects import periodic_modifiers, resolve_resource_target, apply_resource_delta

PDF_RESOURCES = {'hp': {'path': 'sheet.bars.bar_1.value', 'maxPath': 'sheet.bars.bar_1.max', 'min': 0}}


def advance(campaign_id, token_id, *, actor_id=None, new_round=False):
    """Called inside the campaign command transaction; retries use its receipt."""
    if new_round:
        for actor in Actor.objects.filter(campaign_id=campaign_id):
            changed = False
            for effect in actor.data.get('effects', [])[:128]:
                if isinstance(effect, dict) and effect.get('enabled') is not False:
                    changed = _tick_effect(effect)[0] or changed
            if changed:
                persist(actor)
    token = Token.objects.select_related('actor').filter(pk=token_id, scene__campaign_id=campaign_id).first()
    actor = token.actor if token else Actor.objects.filter(pk=actor_id,campaign_id=campaign_id).first() if actor_id else None
    if not actor:
        return
    changed = False
    for entry in periodic_modifiers(actor.data):
        resolved = resolve_resource_target(entry['target'], PDF_RESOURCES)
        if resolved and apply_resource_delta(actor.data, *resolved, entry['delta']) is not None:
            changed = True
    if changed:
        persist(actor)


def persist(actor):
    actor.sheet_version += 1
    actor.version += 1
    actor.save(update_fields=['data','sheet_version','version','updated_at'])
    actor.tokens.filter(linked=True).update(version=F('version')+1)


def _tick_effect(effect: dict[str, Any]) -> tuple[bool, bool]:
    duration = effect.get("duration") if isinstance(effect.get("duration"), dict) else None
    data = effect.get("data") if isinstance(effect.get("data"), dict) else {}
    if duration is None:
        duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
    if not isinstance(duration, dict) or duration.get("type") != "rounds":
        return False, False

    try:
        remaining = int(duration.get("remaining", duration.get("value")))
    except (TypeError, ValueError):
        return False, False
    next_remaining = max(0, remaining - 1)
    duration["remaining"] = next_remaining
    effect["duration"] = duration
    data_duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
    if data_duration is not None:
        data_duration["remaining"] = next_remaining
    if next_remaining <= 0:
        effect["enabled"] = False
        return True, True
    return True, False
