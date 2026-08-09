"""System-defined presentation for roll results.

The Sheet SDK produces roll metadata (action id, source, formula, roll input,
chatCard/rollToast ids). This service resolves those ids against the active
system's declarative mappings and returns a small, safe presentation payload for
chat messages and roll toasts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import config
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sdk.package_locale_service import PackageLocaleService
from app.helpers.i18n import get_configured_default_locale


def _dice_summary(groups: list[dict] | None) -> str:
    """The dice with their notation: ``1d8!>=8 [3, 7] · 1d6!>=6 [2]``.

    A card line can only print a scalar, and the raw groups are a list of dicts.
    This is the verbose form, for a card that wants the notation on the face of
    the message; :func:`_results_summary` is the quiet one.
    """
    parts: list[str] = []
    for group in (groups or [])[:8]:
        if not isinstance(group, dict):
            continue
        notation = str(group.get("notation") or "")
        results = group.get("results")
        if not notation:
            continue
        rolled = ", ".join(str(value) for value in results) if isinstance(results, list) else ""
        parts.append(f"{notation} [{rolled}]" if rolled else notation)
    return " · ".join(parts)


def _results_summary(groups: list[dict] | None) -> str:
    """Only what the dice showed: ``3, 7 · 2``.

    What a player reads off a card is the numbers; the notation that produced
    them is the formula, and belongs in the breakdown behind it.
    """
    parts: list[str] = []
    for group in (groups or [])[:8]:
        results = group.get("results") if isinstance(group, dict) else None
        if not isinstance(results, list) or not results:
            continue
        parts.append(", ".join(str(value) for value in results))
    return " · ".join(parts)


def _group_results(groups: list[dict] | None) -> list[str]:
    """Results split by dice group, ready for declarative card mappings."""
    values: list[str] = []
    for group in (groups or [])[:8]:
        results = group.get("results") if isinstance(group, dict) else None
        values.append(", ".join(str(value) for value in results) if isinstance(results, list) else "")
    return values


def _rich_text_plain(node: Any) -> str:
    """Flatten a ProseMirror/Tiptap document into readable chat text."""
    if isinstance(node, str):
        return node.strip()
    if not isinstance(node, (dict, list)):
        return ""
    if isinstance(node, list):
        return "\n".join(filter(None, (_rich_text_plain(child) for child in node)))
    if node.get("type") == "text":
        return str(node.get("text") or "")
    content = node.get("content")
    if not isinstance(content, list):
        return ""
    parts = [_rich_text_plain(child) for child in content]
    separator = "\n" if node.get("type") in {"doc", "paragraph", "heading", "bulletList", "orderedList", "listItem"} else ""
    return separator.join(filter(None, parts)).strip()


def _all_ones(groups: list[dict] | None) -> bool:
    """Every die rolled showed a 1.

    Several systems make this the worst possible outcome under a name of their
    own (SWADE calls it a critical failure). The engine only reports the fact.
    """
    seen = False
    for group in (groups or [])[:8]:
        results = group.get("results") if isinstance(group, dict) else None
        if not isinstance(results, list) or not results:
            continue
        seen = True
        if any(value != 1 for value in results):
            return False
    return seen


def _outcome(spec: Any, context: dict) -> dict | None:
    """Degrees of success, when the card declares how to measure them.

    ``{"target": 4, "step": 4}`` says a roll succeeds at 4 and gains one more
    degree every 4 over it — SWADE raises, but the shape is not SWADE's: a
    system with a different target, or one that only cares about pass/fail
    (``step`` omitted), declares its own. ``target`` may be an ``@`` path, so a
    dialog that asks for a target number can feed it.
    """
    if not isinstance(spec, dict):
        return None
    total = context["roll"]["total"]
    if not isinstance(total, (int, float)) or isinstance(total, bool):
        return None

    target = spec.get("target")
    if isinstance(target, str) and target.startswith("@"):
        cursor: Any = context
        for segment in target[1:].split("."):
            cursor = cursor.get(segment) if isinstance(cursor, dict) else None
        target = cursor
    try:
        target_value = int(target)
    except (TypeError, ValueError):
        return None

    try:
        step = int(spec.get("step") or 0)
    except (TypeError, ValueError):
        step = 0

    margin = int(total) - target_value
    success = margin >= 0
    steps = margin // step if success and step > 0 else 0
    return {
        "target": target_value,
        "margin": margin,
        "success": success,


        "steps": steps or "",
        "tone": "success" if success else "failure",
    }


@dataclass(frozen=True)
class RollPresentation:
    chat_card: dict | None = None
    roll_toast: dict | None = None

    def as_metadata(self) -> dict:
        payload: dict[str, Any] = {}
        if self.chat_card:
            payload["chatCard"] = self.chat_card
        if self.roll_toast:
            payload["rollToast"] = self.roll_toast
        return payload


class RollPresentationService:
    def __init__(self) -> None:
        self.rules = SystemRulesService()
        self.locales = PackageLocaleService()

    def render(
        self,
        *,
        system_id: str | None,
        metadata: dict | None,
        actor_name: str | None,
        label: str | None,
        expression: str | None,
        groups: list[dict] | None,
        modifier: int | None,
        total: int | None,
    ) -> RollPresentation:
        if not system_id or not isinstance(metadata, dict):
            return RollPresentation(
                chat_card=self._fallback_chat_card(
                    label=label,
                    expression=expression,
                    groups=groups,
                    modifier=modifier,
                    total=total,
                ),
                roll_toast=self._fallback_toast(label=label, expression=expression, total=total),
            )

        presentation = (
            metadata.get("presentation") if isinstance(metadata.get("presentation"), dict) else {}
        )
        chat_card_id = presentation.get("chatCard")
        roll_toast_id = presentation.get("rollToast") or chat_card_id

        context = self._context(
            metadata=metadata,
            actor_name=actor_name,
            label=label,
            expression=expression,
            groups=groups,
            modifier=modifier,
            total=total,
        )



        catalog = self.locales.get_locale(system_id, get_configured_default_locale())
        chat_card = self._render_chat_card(
            system_id=system_id, card_id=chat_card_id, context=context, catalog=catalog
        )
        roll_toast = self._render_roll_toast(
            system_id=system_id, toast_id=roll_toast_id, context=context, catalog=catalog
        )

        return RollPresentation(
            chat_card=chat_card
            or self._fallback_chat_card(
                label=label, expression=expression, groups=groups, modifier=modifier, total=total
            ),
            roll_toast=roll_toast
            or self._fallback_toast(label=label, expression=expression, total=total),
        )

    def _context(
        self,
        *,
        metadata: dict,
        actor_name: str | None,
        label: str | None,
        expression: str | None,
        groups: list[dict] | None,
        modifier: int | None,
        total: int | None,
    ) -> dict:
        source = metadata.get("source") if isinstance(metadata.get("source"), dict) else {}
        formula_payload = (
            metadata.get("formula") if isinstance(metadata.get("formula"), dict) else {}
        )
        display_formula = (
            formula_payload.get("display")
            or formula_payload.get("resolved")
            or formula_payload.get("final")
            or expression
            or ""
        )
        if isinstance(metadata.get("item"), dict) and metadata["item"]:
            item_context = {
                **metadata["item"],
                "name": metadata["item"].get("name") or label or "",
            }
        else:
            item_context = {"id": source.get("itemInstanceId") or "", "name": ""}
        item_data = item_context.get("data") if isinstance(item_context.get("data"), dict) else {}
        item_context["descriptionText"] = _rich_text_plain(item_data.get("description"))

        return {
            "metadata": metadata,
            "actor": {
                "id": metadata.get("actorId") or "",
                "name": actor_name or metadata.get("actorName") or "",
            },
            "action": {
                "id": metadata.get("actionId") or "",
                "label": label or metadata.get("label") or "Roll",
            },



            "item": item_context,
            "roll": {
                "formula": display_formula,
                "baseFormula": formula_payload.get("base") or expression or "",
                "finalFormula": formula_payload.get("final") or expression or "",
                "resolvedFormula": formula_payload.get("resolved") or display_formula,
                "displayFormula": formula_payload.get("display") or display_formula,
                "expression": expression or "",
                "groups": groups or [],
                "dice": _dice_summary(groups),
                "results": _results_summary(groups),
                "groupResults": _group_results(groups),
                "allOnes": _all_ones(groups),
                "modifier": modifier or 0,



                "modifierText": f"{modifier:+d}" if modifier else "",
                "total": total if total is not None else "",
                "kind": metadata.get("intent") or "roll",
                "visibility": metadata.get("visibility") or "public",
            },
            "input": metadata.get("rollInput")
            if isinstance(metadata.get("rollInput"), dict)
            else {},
        }

    def _render_chat_card(
        self, *, system_id: str, card_id: Any, context: dict, catalog: dict[str, str]
    ) -> dict | None:
        if not isinstance(card_id, str) or not card_id:
            return None
        mappings = self.rules.get_chat_card_mappings(system_id)
        cards = mappings.get("cards") if isinstance(mappings.get("cards"), dict) else mappings
        spec = cards.get(card_id) if isinstance(cards, dict) else None
        if not isinstance(spec, dict):
            return None
        outcome = _outcome(spec.get("outcome"), context)
        if outcome is not None:
            critical_failure = bool(context["roll"]["allOnes"])
            outcome["criticalFailure"] = critical_failure
            if critical_failure:


                outcome["success"] = False
                outcome["steps"] = ""
                outcome["tone"] = "critical-failure"
            context = {**context, "outcome": outcome}
        title = self._resolve_field(spec, "title", context, catalog, default="@action.label")



        dynamic_title_key = None
        if not isinstance(spec.get("titleKey"), str) and isinstance(title, str) and title in catalog:
            dynamic_title_key = title
            title = catalog[title]
        title_template_key = spec.get("titleTemplateKey")
        title_template_args: dict[str, str] = {}
        raw_template_args = spec.get("titleTemplateArgs")
        if isinstance(title_template_key, str) and isinstance(raw_template_args, dict):
            title_template_args = {
                str(key): str(self._resolve(value, context) or "")
                for key, value in raw_template_args.items()
            }


            if all(title_template_args.values()):
                template = catalog.get(title_template_key, title)
                for key, value in title_template_args.items():
                    template = template.replace("{" + key + "}", value)
                title = template
            else:
                title_template_key = None
                title_template_args = {}
        subtitle = self._resolve_field(spec, "subtitle", context, catalog, default="")
        lines = []
        raw_lines = spec.get("lines")
        if isinstance(raw_lines, list):
            for line in raw_lines[:12]:
                if not isinstance(line, dict):
                    continue
                label = self._resolve_field(line, "label", context, catalog, default="")
                value = self._resolve(line.get("value", ""), context)
                if value in (None, ""):
                    continue
                rendered_line = {"label": str(label or ""), "value": str(value)}
                if isinstance(line.get("labelKey"), str):
                    rendered_line["labelKey"] = line["labelKey"]
                lines.append(rendered_line)
        card = {
            "id": card_id,



            "system": system_id,
            "title": str(title or ""),
            "subtitle": str(subtitle or ""),
            "lines": lines,
            "total": context["roll"]["total"],
        }



        if isinstance(spec.get("titleKey"), str):
            card["titleKey"] = spec["titleKey"]
        elif dynamic_title_key:
            card["titleKey"] = dynamic_title_key
        if title_template_key:
            card.pop("titleKey", None)
            card["titleTemplateKey"] = title_template_key
            card["titleTemplateArgs"] = title_template_args
        if isinstance(spec.get("subtitleKey"), str):
            card["subtitleKey"] = spec["subtitleKey"]
        if outcome is not None:
            card["tone"] = outcome["tone"]
            status_keys = spec.get("statusKeys")
            if isinstance(status_keys, dict):
                status_id = (
                    "criticalFailure"
                    if outcome["criticalFailure"]
                    else "success"
                    if outcome["success"]
                    else "failure"
                )
                status_key = status_keys.get(status_id)
                if isinstance(status_key, str):
                    card["statusKey"] = status_key
                    card["status"] = catalog.get(status_key, status_id)



        if spec.get("dice") is not False:
            card["groups"] = context["roll"]["groups"]
            card["modifier"] = context["roll"]["modifier"]
        return card

    def _render_roll_toast(
        self, *, system_id: str, toast_id: Any, context: dict, catalog: dict[str, str]
    ) -> dict | None:
        if not isinstance(toast_id, str) or not toast_id:
            return None
        mappings = self.rules.get_roll_toast_mappings(system_id)
        toasts = mappings.get("toasts") if isinstance(mappings.get("toasts"), dict) else mappings
        spec = toasts.get(toast_id) if isinstance(toasts, dict) else None
        if not isinstance(spec, dict):
            return None
        return {
            "id": toast_id,
            "title": str(
                self._resolve_field(spec, "title", context, catalog, default="@action.label") or ""
            ),
            "subtitle": str(
                self._resolve_field(spec, "subtitle", context, catalog, default="") or ""
            ),
            "formula": str(self._resolve(spec.get("formula", "@roll.formula"), context) or ""),
            "total": self._resolve(spec.get("total", "@roll.total"), context),
            "kind": str(self._resolve(spec.get("kind", "@roll.kind"), context) or "roll"),
        }

    def _resolve_field(
        self, spec: dict, field: str, context: dict, catalog: dict[str, str], *, default: str = ""
    ) -> Any:
        """Resolve a presentation field, preferring a ``{field}Key`` locale lookup.

        A ``labelKey``/``titleKey``/``subtitleKey`` resolves against the system
        locale catalog; otherwise the literal ``{field}`` (which may be an
        ``@``-context path) is used.
        """
        locale_key = spec.get(f"{field}Key")
        if isinstance(locale_key, str) and locale_key in catalog:
            return catalog[locale_key]
        return self._resolve(spec.get(field, default), context)

    def _resolve(self, node: Any, context: dict) -> Any:
        if isinstance(node, dict):
            return {key: self._resolve(value, context) for key, value in node.items()}
        if isinstance(node, list):
            return [self._resolve(item, context) for item in node]
        if not isinstance(node, str) or not node.startswith("@"):
            return node
        cursor: Any = context
        for segment in node[1:].split("."):
            if isinstance(cursor, dict):
                cursor = cursor.get(segment)
            elif isinstance(cursor, list) and segment.isdigit():
                index = int(segment)
                cursor = cursor[index] if index < len(cursor) else None
            else:
                return ""
        return cursor if cursor is not None else ""

    def _fallback_chat_card(
        self,
        *,
        label: str | None,
        expression: str | None,
        groups: list[dict] | None,
        modifier: int | None,
        total: int | None,
    ) -> dict:
        lines = []
        if expression:
            lines.append({"label": "Fórmula", "value": str(expression)})
        if groups:
            breakdown = []
            for group in groups[:8]:
                notation = group.get("notation") if isinstance(group, dict) else ""
                results = group.get("results") if isinstance(group, dict) else []
                if notation:
                    dice = ", ".join(str(r) for r in results) if isinstance(results, list) else ""
                    breakdown.append(f"{notation}: [{dice}]")
            if breakdown:
                lines.append({"label": "Dados", "value": " · ".join(breakdown)})
        if modifier:
            lines.append({"label": "Modificador", "value": f"{modifier:+d}"})
        return {
            "id": "default",
            "title": label or "Roll",
            "subtitle": "",
            "lines": lines,
            "total": total if total is not None else "",
        }

    def _fallback_toast(
        self, *, label: str | None, expression: str | None, total: int | None
    ) -> dict:
        return {
            "id": "default",
            "title": label or "Roll",
            "subtitle": expression or "",
            "formula": expression or "",
            "total": total if total is not None else "",
            "kind": "roll",
        }
