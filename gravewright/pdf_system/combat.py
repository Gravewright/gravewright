"""Combat conventions owned by the bundled PDF system, not the encounter host.

Existing PDF effects use the first mapped bar, named damage/healing operations
and round-based clocks. Keep those document conventions here for compatibility.
"""
from copy import deepcopy
import math

from gravewright.combat import formula_engine
from gravewright.combat.active_effects import (
    active_effects, apply_resource_delta, effect_modifiers, resolve_resource_target,
)


RESOURCES = {'hp': {'path': 'sheet.bars.bar_1.value', 'maxPath': 'sheet.bars.bar_1.max', 'min': 0}}


def _selected_effects(data):
    selected = []
    for effect in active_effects(data):
        payload = effect.get('data') if isinstance(effect.get('data'), dict) else {}
        condition = payload.get('condition')
        if isinstance(condition, str) and condition.strip():
            try:
                if not formula_engine.evaluate(condition, context={'sheet': data}).total:
                    continue
            except formula_engine.FormulaError:
                continue
        selected.append(effect)
    return selected


def _adjust_incoming_damage(data, amount, damage_type, effects):
    targets = {'damage.received'}
    if damage_type:
        targets.add(f'damage.received.{damage_type.lower()}')
    modifiers, _ = effect_modifiers(data, targets, effects=effects)
    operations = {modifier.get('operation') for modifier in modifiers}
    if 'immunity' in operations:
        return 0
    for modifier in modifiers:
        if modifier.get('operation') == 'reduce':
            try:
                amount -= max(0, int(modifier.get('value') or 0))
            except (TypeError, ValueError, OverflowError):
                continue
    amount = max(0, amount)
    if 'resistance' in operations:
        amount //= 2
    if 'vulnerability' in operations:
        amount *= 2
    return amount


def periodic_modifiers(data, *, roller=None):
    """Translate the PDF system's legacy effect operations into bar deltas."""
    selected = _selected_effects(data)
    result = []
    for effect in selected:
        payload = effect.get('data') if isinstance(effect.get('data'), dict) else {}
        modifiers = payload.get('modifiers') or effect.get('modifiers') or []
        if not isinstance(modifiers, list):
            continue
        for modifier in modifiers[:32]:
            if not isinstance(modifier, dict):
                continue
            operation = modifier.get('operation')
            if operation not in ('damage_over_time', 'heal_over_time'):
                continue
            value = modifier.get('value')
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                continue
            try:
                rolled = formula_engine.evaluate(str(value), roller=roller).total
                if not math.isfinite(rolled):
                    continue
                rolled = max(0, int(rolled))
            except (formula_engine.FormulaError, ValueError, OverflowError):
                continue
            damage_type = str(modifier.get('damageType') or modifier.get('damage_type') or '')
            amount = (_adjust_incoming_damage(data, rolled, damage_type, selected)
                      if operation == 'damage_over_time' else rolled)
            if amount:
                result.append({
                    'target': str(modifier.get('target') or '').strip(),
                    'delta': -amount if operation == 'damage_over_time' else amount,
                })
    return result


def _duration(effect):
    payload = effect.get('data') if isinstance(effect.get('data'), dict) else {}
    return (payload.get('duration') if isinstance(payload.get('duration'), dict)
            else effect.get('duration'))


def _clock_matches(duration, event):
    if not isinstance(duration, dict) or duration.get('type') not in ('rounds', 'turns'):
        return False
    expiry = duration.get('expires')
    if not expiry:
        return duration.get('type') == 'rounds' and event.get('phase') == 'end' and event.get('roundBoundary', False)
    if expiry not in ('start', 'end') or expiry != event.get('phase'):
        return False
    if duration.get('sourceTokenId'):
        return str(duration['sourceTokenId']) == event.get('tokenId')
    if duration.get('sourceActorId'):
        return str(duration['sourceActorId']) == event.get('actorId')
    return bool(event.get('isCurrent'))


def _tick_effect(effect):
    duration = _duration(effect)
    try:
        raw = duration.get('remaining', duration.get('value'))
        remaining = int(raw)
        if isinstance(raw, bool) or float(raw) != remaining or not 0 <= remaining <= 10000:
            return False
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
    duration = {**duration, 'remaining': max(0, remaining - 1)}
    effect['duration'] = deepcopy(duration)
    payload = effect.get('data') if isinstance(effect.get('data'), dict) else {}
    if isinstance(payload.get('duration'), dict):
        payload['duration'] = deepcopy(duration)
    if duration['remaining'] == 0:
        effect['enabled'] = False
    return True


def advance_effects(data, event):
    """Handle PDF clocks and resources on the document selected by the host."""
    if not isinstance(data, dict) or not isinstance(event, dict) or event.get('phase') not in ('start', 'end'):
        return False
    changed = False
    effects = data.get('effects', [])
    if not isinstance(effects, list):
        return False
    clock_keys = event.get('clockKeys', set())
    for index, effect in enumerate(effects[:128]):
        if not isinstance(effect, dict) or effect.get('enabled') is False:
            continue
        payload = effect.get('data') if isinstance(effect.get('data'), dict) else {}
        if payload.get('enabled') is False:
            continue
        key = (*event.get('documentKey', ()), index, event.get('phase'))
        if key not in clock_keys and _clock_matches(_duration(effect), event):
            if _tick_effect(effect):
                clock_keys.add(key)
                changed = True
    if event.get('phase') == 'start' and event.get('isCurrent') and event.get('periodic', True):
        for modifier in periodic_modifiers(data):
            target = modifier['target']
            if target in ('', 'damage.self', 'heal.self', 'self'):
                target = 'resource.hp'
            resolved = resolve_resource_target(target, RESOURCES)
            if resolved and apply_resource_delta(data, *resolved, modifier['delta']) is not None:
                changed = True
    return changed
