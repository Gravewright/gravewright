"""Server-authoritative execution of sheet actions (§9.3, command ``sheet.action.execute``).

Loads the Actor Core + Sheet Data, applies the system's derived fields, then
interprets the declarative action:

* ``roll``   — evaluate the formula (rolling dice), produce a chat/roll-toast payload
* ``patch``  — evaluate patch expressions and persist them (version bump)
* ``append`` — resolve a value template and append it to a target list (used by drop)

All formulas run through the no-eval :mod:`formula_engine`. Nothing here imports
Litestar; the HTTP layer broadcasts chat/roll-toast and realtime events.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from typing import Any
from uuid import uuid4

from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.effects.active_effects import (
    adjust_incoming_damage,
    apply_resource_delta,
    apply_roll_modifiers,
    apply_stat_modifiers,
    effect_modifiers,
    resolve_resource_target,
)
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.formula_engine import FormulaError, evaluate
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_repository import TokenRepository


@dataclass(frozen=True)
class ActionResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    actor_name: str | None = None
    action_type: str | None = None
    label: str | None = None
          
    expression: str | None = None
    groups: list[dict] = field(default_factory=list)
    modifier: int = 0
    total: int = 0
    visibility: str = "public"
    chat_card: str | None = None
    roll_toast: str | None = None
    base_formula: str | None = None
    final_formula: str | None = None
    resolved_formula: str | None = None
    display_formula: str | None = None
    roll_input: dict = field(default_factory=dict)
    intent: str | None = None
    source: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
                    
    version: int | None = None
    changed_paths: list[str] = field(default_factory=list)
    token_view: dict | None = None
                                            
    applied: dict | None = None
    error_key: str | None = None


def _display_expression(formula_groups: list[dict], modifier: int, total: int) -> str:
    if not formula_groups:
        return str(total)
    parts = [group["notation"] for group in formula_groups]
    text = " + ".join(parts)
    if modifier:
        text += f" {'+' if modifier > 0 else '-'} {abs(modifier)}"
    return text


def _resolve_template(node: Any, lookup: dict) -> Any:
    """Resolve a value template: ``"@a.b"`` -> lookup path; dicts/lists recurse."""
    if isinstance(node, dict):
        return {key: _resolve_template(value, lookup) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_template(item, lookup) for item in node]
    if isinstance(node, str) and node.startswith("@"):
        cursor: Any = lookup
        for segment in node[1:].split("."):
            if isinstance(cursor, dict):
                cursor = cursor.get(segment)
            else:
                cursor = None
                break
        return cursor
    return node


_DICE_RE = re.compile(r"^[1-9][0-9]?d[1-9][0-9]{0,2}$")
_D20_RE = re.compile(r"(?<![A-Za-z0-9_])1d20(?![A-Za-z0-9_])", re.IGNORECASE)


_PATH_REF_RE = re.compile(r"@([A-Za-z0-9_.]+)")


def _lookup_dotted(root: dict, dotted: str) -> Any:
    cursor: Any = root
    for segment in str(dotted or "").split("."):
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _formula_value_for_display(value: Any) -> str:
                                                                                 
                                                                      
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return "0"


def _resolve_formula_paths_for_display(formula: str, *, context: dict, scope: dict) -> str:
    if not isinstance(formula, str) or "@" not in formula:
        return formula

    def repl(match: re.Match[str]) -> str:
        path = match.group(1)
        root, _, rest = path.partition(".")
        if root in context:
            value = _lookup_dotted(context[root], rest) if rest else context[root]
        elif root in scope:
            value = _lookup_dotted(scope[root], rest) if rest else scope[root]
        else:
            value = None
        return _formula_value_for_display(value)

    return _PATH_REF_RE.sub(repl, formula)


def _input_value(inputs: dict, path: str) -> Any:
    cursor: Any = inputs
    for segment in str(path or "").split("."):
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _literal_value(raw: str) -> Any:
    text = raw.strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        return int(text)
    except ValueError:
        return text


def _condition_matches(condition: object, inputs: dict) -> bool:
    """Very small no-eval predicate language for roll transforms.

    Supported forms:
      input.mode == 'advantage'
      input.extraModifier != 0
      input.extraDice
    """
    if condition in (None, "", True):
        return True
    if condition is False or not isinstance(condition, str):
        return False
    text = condition.strip()
    for op in ("==", "!="):
        if op in text:
            left, right = [part.strip() for part in text.split(op, 1)]
            if not left.startswith("input."):
                return False
            value = _input_value(inputs, left[len("input."):])
            expected = _literal_value(right)
            return (value == expected) if op == "==" else (value != expected)
    if text.startswith("input."):
        return bool(_input_value(inputs, text[len("input."):]))
    return False


def _resolve_input_ref(value: object, inputs: dict) -> Any:
    if isinstance(value, str) and value.startswith("@input."):
        return _input_value(inputs, value[len("@input."):])
    return value


def _append_formula_part(formula: str, value: Any, *, user_supplied: bool = False) -> str:
    if isinstance(value, bool) or value in (None, ""):
        return formula
    if isinstance(value, (int, float)):
        numeric = max(-999, min(999, int(value)))
        if not numeric:
            return formula
        return f"{formula} {'+' if numeric > 0 else '-'} {abs(numeric)}"
    text = str(value).strip()
    if not text:
        return formula
                                                                                    
                                                                               
    if user_supplied and not _DICE_RE.fullmatch(text):
        return formula
    if text.startswith("-"):
        return f"{formula} - {text[1:].strip()}"
    return f"{formula} + {text}"


def _apply_roll_transforms(formula: str, action: dict, roll_options: dict | None) -> str:
    if not isinstance(roll_options, dict):
        return formula

    transforms = action.get("transforms")
    if not isinstance(transforms, list):
                                                                                
                                          
        return _apply_legacy_roll_options(formula, roll_options)

    next_formula = formula
    for transform in transforms[:16]:
        if not isinstance(transform, dict):
            continue
        if not _condition_matches(transform.get("when"), roll_options):
            continue

        replace = transform.get("replaceFirstDie")
        if isinstance(replace, dict):
            source = str(replace.get("from") or "")
            target = str(replace.get("to") or "")
            if source and target:
                pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(source)}(?![A-Za-z0-9_])", re.IGNORECASE)
                next_formula = pattern.sub(target, next_formula, count=1)

        if "append" in transform:
            value = _resolve_input_ref(transform.get("append"), roll_options)
            next_formula = _append_formula_part(next_formula, value, user_supplied=isinstance(transform.get("append"), str) and transform.get("append", "").startswith("@input."))

        if "appendEach" in transform:
            values = _resolve_input_ref(transform.get("appendEach"), roll_options)
            if isinstance(values, list):
                for value in values[:8]:
                    next_formula = _append_formula_part(next_formula, value, user_supplied=True)

    return next_formula


def _apply_legacy_roll_options(formula: str, roll_options: dict | None) -> str:
    if not isinstance(roll_options, dict):
        return formula

    next_formula = formula
    mode = str(roll_options.get("mode") or "normal")
    if mode == "advantage":
        next_formula = _D20_RE.sub("2d20kh1", next_formula, count=1)
    elif mode == "disadvantage":
        next_formula = _D20_RE.sub("2d20kl1", next_formula, count=1)

    extra_dice = roll_options.get("extraDice")
    if isinstance(extra_dice, list):
        for notation in extra_dice[:5]:
            die = str(notation).strip()
            if _DICE_RE.fullmatch(die):
                next_formula += f" + {die}"

    try:
        extra_modifier = int(roll_options.get("extraModifier") or 0)
    except (TypeError, ValueError):
        extra_modifier = 0
    extra_modifier = max(-999, min(999, extra_modifier))
    if extra_modifier:
        next_formula += f" {'+' if extra_modifier > 0 else '-'} {abs(extra_modifier)}"

    return next_formula


def _roll_visibility(default: object, roll_options: dict | None) -> str:
    fallback = str(default or "public")
    if not isinstance(roll_options, dict):
        return fallback
    visibility = str(roll_options.get("visibility") or fallback)
    return visibility if visibility in {"public", "gm", "blind_gm", "self"} else fallback


def _roll_targets(action_id: str | None, action: dict) -> set[str]:
    action_key = str(action_id or "")
    dialog = action.get("dialog") if isinstance(action.get("dialog"), dict) else {}
    intent = str(dialog.get("intent") or action.get("intent") or "").strip()
    targets = {"roll.any"}
    if action_key:
        targets.add(f"action.{action_key}")
        if action_key.startswith("roll.save."):
            targets.add(action_key)
        if action_key.startswith("roll.check."):
            targets.add(action_key)
        if action_key.startswith("roll.skill."):
            targets.add(action_key)
    if intent:
        targets.add(f"roll.{intent}")
    lowered = action_key.lower()
    chat_card = str(action.get("chatCard") or "").lower()
    probe = f"{lowered} {chat_card} {intent}".lower()
    if "attack" in probe:
        targets.add("roll.attack")
    if "damage" in probe or "dano" in probe:
        targets.add("roll.damage")
    if ".save" in lowered or lowered.startswith("roll.save") or "save" in probe or "salvaguarda" in probe:
        targets.add("roll.save")
    if lowered.startswith("roll.ability") or "check" in probe or "teste" in probe:
        targets.add("roll.check")
    return targets



class SheetActionService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.scenes = SceneRepository()
        self.tokens = TokenRepository()
        self.storage = ScopedJsonStorage()
        self.systems = PackageInstallService()
        self.rules = SystemRulesService()

    def execute(
        self,
        *,
        actor_id: str,
        action_id: str,
        user_id: str,
        inputs: dict | None = None,
        drop: dict | None = None,
        item: dict | None = None,
        roll_options: dict | None = None,
        target_actor_id: str | None = None,
        target_token_id: str | None = None,
    ) -> ActionResult:
        ctx = self._load(actor_id, user_id)
        if ctx.error is not None:
            return ctx.error
        actor, campaign = ctx.actor, ctx.campaign

        action = self.rules.get_action(actor["system_id"], action_id)
        if action is None:
            return ActionResult(success=False, error_key="game.actions.errors.action_not_found")
        action_type = action.get("type")

        needs_edit = action_type in {"patch", "append"}
        allowed = (
            can_edit_actor(actor=actor, campaign=campaign, user_id=user_id)
            if needs_edit
            else can_view_actor(actor=actor, campaign=campaign, user_id=user_id)
        )
        if not allowed:
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        effective_data = apply_stat_modifiers(derived_data)
        context = {"core": core, "sheet": effective_data, "item": item or {}}
        scope = {"input": inputs or {}, "drop": drop or {}}

        if action_type == "roll":
            result = self._do_roll(
                actor,
                action,
                context,
                scope,
                helpers,
                action_id=action_id,
                item=item if isinstance(item, dict) else None,
                roll_options=roll_options,
            )
            apply_directive = action.get("apply")
            if result.success and isinstance(apply_directive, dict) and (target_token_id or target_actor_id):
                lookup = {**context, "input": scope.get("input", {}), "drop": scope.get("drop", {})}
                if target_token_id:
                    return self._apply_to_target_token(
                        roll_result=result,
                        requester_user_id=user_id,
                        target_token_id=target_token_id,
                        directive=apply_directive,
                        lookup=lookup,
                    )
                return self._apply_to_target(
                    roll_result=result,
                    requester_user_id=user_id,
                    target_actor_id=target_actor_id or "",
                    directive=apply_directive,
                    lookup=lookup,
                )
            return result
        if action_type == "patch":
            return self._do_patch(actor, action, data, context, scope, helpers, envelope, core, derived)
        if action_type == "append":
            return self._do_append(actor, action, data, context, scope, envelope, core, derived, helpers)
        return ActionResult(success=False, error_key="game.actions.errors.unsupported_type")

    def roll_formula(
        self, *, actor_id: str, formula: str, user_id: str, label: str = "", roll_options: dict | None = None
    ) -> ActionResult:
        ctx = self._load(actor_id, user_id)
        if ctx.error is not None:
            return ctx.error
        actor, campaign = ctx.actor, ctx.campaign
        if not can_view_actor(actor=actor, campaign=campaign, user_id=user_id):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        effective_data = apply_stat_modifiers(derived_data)
        context = {"core": core, "sheet": effective_data, "item": {}}
        return self._do_roll(
            actor,
            {"formula": formula, "label": label or "Roll", "visibility": "public"},
            context,
            {"input": {}, "drop": {}},
            helpers,
            action_id="dice.roll",
            item=None,
            roll_options=roll_options,
        )

                                                                                

    def _do_roll(
        self,
        actor,
        action,
        context,
        scope,
        helpers,
        *,
        action_id: str | None = None,
        item: dict | None = None,
        roll_options: dict | None = None,
    ) -> ActionResult:
        formula = action.get("formula")
        if not isinstance(formula, str):
            return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
        base_formula = formula
        lookup = {**context, "input": scope.get("input", {}), "drop": scope.get("drop", {})}
        resolved_formula = _resolve_template(formula, lookup)
        if isinstance(resolved_formula, str) and resolved_formula:
            formula = resolved_formula
        final_formula = _apply_roll_transforms(formula, action, roll_options)
        active_modifiers, applied_effects = effect_modifiers(
            context.get("sheet", {}),
            _roll_targets(action_id, action),
        )
        final_formula = apply_roll_modifiers(final_formula, active_modifiers)
        label = action.get("label") or "Roll"
        if isinstance(label, str) and label.startswith("@"):
            resolved_label = _resolve_template(label, lookup)
            label = str(resolved_label) if resolved_label not in (None, "") else "Roll"
        try:
            result = evaluate(final_formula, context=context, scope=scope, helpers=helpers)
        except FormulaError:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
        resolved_formula_for_display = _resolve_formula_paths_for_display(
            final_formula,
            context=context,
            scope=scope,
        )
        display_formula = _display_expression(result.groups, result.modifier, result.int_total)
        visibility = _roll_visibility(action.get("visibility", "public"), roll_options)
        dialog = action.get("dialog") if isinstance(action.get("dialog"), dict) else {}
        roll_input = dict(roll_options) if isinstance(roll_options, dict) else {}
        source = (
            {"kind": "actor_item_instance", "itemInstanceId": str(item.get("id"))}
            if isinstance(item, dict) and item.get("id")
            else {"kind": "actor", "actorId": actor["id"]}
        )
        metadata = {
            "actionId": action_id or "",
            "actorId": actor["id"],
            "actorName": actor["name"],
            "systemId": actor["system_id"],
            "label": str(label or "Roll"),
            "intent": str(dialog.get("intent") or action.get("intent") or ""),
            "source": source,
            "formula": {
                "base": base_formula,
                "final": final_formula,
                "resolved": resolved_formula_for_display,
                "display": display_formula,
            },
            "rollInput": roll_input,
            "effects": applied_effects,
            "presentation": {
                "chatCard": action.get("chatCard"),
                "rollToast": action.get("rollToast"),
            },
            "visibility": visibility,
        }
        return ActionResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            actor_name=actor["name"],
            action_type="roll",
            label=label,
            expression=display_formula,
            groups=result.groups,
            modifier=result.modifier,
            total=result.int_total,
            visibility=visibility,
            chat_card=action.get("chatCard"),
            roll_toast=action.get("rollToast"),
            base_formula=base_formula,
            final_formula=final_formula,
            resolved_formula=resolved_formula_for_display,
            display_formula=display_formula,
            roll_input=roll_input,
            intent=metadata["intent"] or None,
            source=source,
            metadata=metadata,
        )

    def _apply_to_target(
        self, *, roll_result: ActionResult, requester_user_id: str, target_actor_id: str,
        directive: dict, lookup: dict,
    ) -> ActionResult:
        """Apply a rolled total to a target actor's resource (damage or heal).

        Damage routes through the target's resistance/vulnerability/immunity via
        ``adjust_incoming_damage``; the resource path comes from the target
        system's combat ``resources`` config. Requires edit access on the target.
        """
        target = self.actors.get(target_actor_id)
        if target is None or target["status"] != "active":
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        if target["campaign_id"] != roll_result.campaign_id:
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        target_campaign = self.campaigns.get_for_user(
            campaign_id=target["campaign_id"], user_id=requester_user_id
        )
        if target_campaign is None:
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        if not can_edit_actor(actor=target, campaign=dict(target_campaign), user_id=requester_user_id):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        mode = "heal" if str(directive.get("mode") or "damage") == "heal" else "damage"
        amount = max(0, int(roll_result.total))

        envelope = self.storage.read_actor(
            system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target_actor_id
        ) or {"version": 1, "data": {}}
        target_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        combat = self.rules.get_combat_config(target["system_id"])
        resources = combat.get("resources") if isinstance(combat.get("resources"), dict) else {}

        if mode == "heal":
            damage_type = ""
            applied = amount
            resolved = resolve_resource_target("heal.self", resources)
            delta = applied
        else:
            raw_type = directive.get("damageType")
            damage_type = str(_resolve_template(raw_type, lookup) or "") if raw_type else ""
            applied = adjust_incoming_damage(target_data, amount, damage_type)
            resolved = resolve_resource_target("damage.self", resources)
            delta = -applied

        if resolved is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")
        value_path, max_path, floor = resolved
        value_after = apply_resource_delta(target_data, value_path, max_path, floor, delta)
        if value_after is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=target["system_id"], campaign_id=target["campaign_id"],
            actor_id=target_actor_id, version=version, data=target_data,
        )
        return replace(roll_result, applied={
            "targetActorId": target_actor_id,
            "targetName": target["name"],
            "campaignId": target["campaign_id"],
            "systemId": target["system_id"],
            "mode": mode,
            "rawAmount": amount,
            "amount": applied,
            "damageType": damage_type,
            "resourcePath": value_path,
            "valueAfter": value_after,
            "version": version,
        })

    def _apply_to_target_token(
        self, *, roll_result: ActionResult, requester_user_id: str, target_token_id: str,
        directive: dict, lookup: dict,
    ) -> ActionResult:
        token = self.tokens.get_by_id(target_token_id)
        if token is None or not token.get("actor_id"):
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        scene = self.scenes.get_by_id(token["scene_id"])
        if scene is None or scene["campaign_id"] != roll_result.campaign_id:
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        target = self.actors.get(token["actor_id"])
        if target is None or target["status"] != "active" or target["campaign_id"] != scene["campaign_id"]:
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        target_campaign = self.campaigns.get_for_user(
            campaign_id=scene["campaign_id"], user_id=requester_user_id
        )
        if target_campaign is None:
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        if not can_edit_actor(actor=target, campaign=dict(target_campaign), user_id=requester_user_id):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        is_unlinked = token.get("actor_link_mode") == "unlinked"
        if is_unlinked:
            overrides = dict(token.get("overrides") or {})
            instance = overrides.get("_actor_instance")
            if not isinstance(instance, dict):
                base = self.storage.read_actor(
                    system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"]
                ) or {"version": 1, "data": {}}
                instance = {
                    "source_actor_id": target["id"],
                    "name": target["name"],
                    "type": target["type"],
                    "system_id": target["system_id"],
                    "version": int(base.get("version", 1)),
                    "data": dict(base.get("data") if isinstance(base.get("data"), dict) else {}),
                }
            target_data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
        else:
            envelope = self.storage.read_actor(
                system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"]
            ) or {"version": 1, "data": {}}
            target_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        mode = "heal" if str(directive.get("mode") or "damage") == "heal" else "damage"
        amount = max(0, int(roll_result.total))
        combat = self.rules.get_combat_config(target["system_id"])
        resources = combat.get("resources") if isinstance(combat.get("resources"), dict) else {}

        if mode == "heal":
            damage_type = ""
            applied = amount
            resolved = resolve_resource_target("heal.self", resources)
            delta = applied
        else:
            raw_type = directive.get("damageType")
            damage_type = str(_resolve_template(raw_type, lookup) or "") if raw_type else ""
            applied = adjust_incoming_damage(target_data, amount, damage_type)
            resolved = resolve_resource_target("damage.self", resources)
            delta = -applied

        if resolved is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")
        value_path, max_path, floor = resolved
        value_after = apply_resource_delta(target_data, value_path, max_path, floor, delta)
        if value_after is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")

        if is_unlinked:
            instance["data"] = target_data
            instance["version"] = int(instance.get("version", 1)) + 1
            overrides["_actor_instance"] = instance
            token_view = self._token_view(
                target,
                target_data,
                {"name": instance.get("name") or token.get("name") or target["name"]},
                self.rules.get_derived(target["system_id"]),
                self.rules.get_helpers(target["system_id"]),
            )
            bars = token_view.get("bars")
            if isinstance(bars, dict):
                overrides.update(bars)
            effects = token_view.get("effects")
            if isinstance(effects, list):
                overrides["effects"] = effects
            updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
            version = int(instance["version"])
            token_version = updated["version"] if updated else token.get("version")
        else:
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(
                system_id=target["system_id"], campaign_id=target["campaign_id"],
                actor_id=target["id"], version=version, data=target_data,
            )
            token_version = token.get("version")

        return replace(roll_result, applied={
            "targetActorId": target["id"],
            "targetTokenId": target_token_id,
            "targetName": token.get("name") or target["name"],
            "campaignId": target["campaign_id"],
            "sceneId": token["scene_id"],
            "systemId": target["system_id"],
            "mode": mode,
            "rawAmount": amount,
            "amount": applied,
            "damageType": damage_type,
            "resourcePath": value_path,
            "valueAfter": value_after,
            "version": version,
            "tokenVersion": token_version,
        })

    def _do_patch(self, actor, action, data, context, scope, helpers, envelope, core, derived) -> ActionResult:
        patch = action.get("patch")
        if not isinstance(patch, dict) or not patch:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_patch")
        for path, expression in patch.items():
            if not isinstance(expression, str):
                continue
            try:
                value = evaluate(expression, context=context, scope=scope, helpers=helpers).total
            except FormulaError:
                return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
            numeric = int(value) if float(value).is_integer() else value
            target = path[len("sheet.") :] if path.startswith("sheet.") else path
            _set_path(data, target, numeric)

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"],
            actor_id=actor["id"], version=version, data=data,
        )
        return self._mutation_result(actor, action, data, version, sorted(patch.keys()), core, derived, helpers)

    def _do_append(self, actor, action, data, context, scope, envelope, core, derived, helpers) -> ActionResult:
        target = action.get("target")
        if not isinstance(target, str) or not target:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_target")
        lookup = {
            **context,
            "input": scope.get("input", {}),
            "drop": scope.get("drop", {}),
            "id": {"uuid": f"actor_item_{uuid4().hex[:12]}"},
        }
        value = _resolve_template(action.get("value"), lookup)
        if isinstance(value, dict) and not value.get("id"):
            value = {"id": f"actor_item_{uuid4().hex[:12]}", **value}
        target_key = target[len("sheet.") :] if target.startswith("sheet.") else target
        current = _get_path(data, target_key)
        items = list(current) if isinstance(current, list) else []
        items.append(value)
        _set_path(data, target_key, items)

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"],
            actor_id=actor["id"], version=version, data=data,
        )
        return self._mutation_result(actor, action, data, version, [target], core, derived, helpers)

    def _mutation_result(self, actor, action, data, version, changed_paths, core, derived, helpers) -> ActionResult:
        token_view = self._token_view(actor, data, core, derived, helpers)
        return ActionResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            actor_name=actor["name"],
            action_type=action.get("type"),
            label=action.get("label"),
            version=version,
            changed_paths=changed_paths,
            token_view=token_view,
        )

    def _token_view(self, actor, data, core, derived, helpers) -> dict:
        mappings = self.rules.get_token_mappings(actor["system_id"])
        if not mappings:
            return {}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        return resolve_token_view(
            actor_type=actor["type"], sheet_data=derived_data, core=core, token_mappings=mappings
        )

                                                                              

    def _load(self, actor_id: str, user_id: str) -> _LoadCtx:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return _LoadCtx(error=ActionResult(success=False, error_key="game.actors.errors.not_found"))
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return _LoadCtx(error=ActionResult(success=False, error_key="game.actors.errors.not_found"))
        if self.systems.get_active_manifest(actor["system_id"]) is None:
            return _LoadCtx(error=ActionResult(success=False, error_key="game.actors.errors.system_not_enabled"))
        return _LoadCtx(actor=actor, campaign=dict(campaign))


@dataclass
class _LoadCtx:
    actor: dict | None = None
    campaign: dict | None = None
    error: ActionResult | None = None


def _set_path(data: dict, dotted: str, value: Any) -> None:
    segments = [segment for segment in dotted.split(".") if segment]
    if not segments:
        return
    cursor = data
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    cursor[segments[-1]] = value


def _get_path(data: dict, dotted: str) -> Any:
    cursor: Any = data
    for segment in dotted.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor
