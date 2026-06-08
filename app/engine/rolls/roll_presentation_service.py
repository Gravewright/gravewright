"""System-defined presentation for roll results.

The Sheet SDK produces roll metadata (action id, source, formula, roll input,
chatCard/rollToast ids). This service resolves those ids against the active
system's declarative mappings and returns a small, safe presentation payload for
chat messages and roll toasts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.rules.rules_registry import SystemRulesService


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
                chat_card=self._fallback_chat_card(label=label, expression=expression, groups=groups, modifier=modifier, total=total),
                roll_toast=self._fallback_toast(label=label, expression=expression, total=total),
            )

        presentation = metadata.get("presentation") if isinstance(metadata.get("presentation"), dict) else {}
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
        chat_card = self._render_chat_card(system_id=system_id, card_id=chat_card_id, context=context)
        roll_toast = self._render_roll_toast(system_id=system_id, toast_id=roll_toast_id, context=context)

        return RollPresentation(
            chat_card=chat_card or self._fallback_chat_card(label=label, expression=expression, groups=groups, modifier=modifier, total=total),
            roll_toast=roll_toast or self._fallback_toast(label=label, expression=expression, total=total),
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
        formula_payload = metadata.get("formula") if isinstance(metadata.get("formula"), dict) else {}
        display_formula = (
            formula_payload.get("display")
            or formula_payload.get("resolved")
            or formula_payload.get("final")
            or expression
            or ""
        )
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
            "item": {
                "id": source.get("itemInstanceId") or "",
                "name": label or metadata.get("label") or "",
            },
            "roll": {
                "formula": display_formula,
                "baseFormula": formula_payload.get("base") or expression or "",
                "finalFormula": formula_payload.get("final") or expression or "",
                "resolvedFormula": formula_payload.get("resolved") or display_formula,
                "displayFormula": formula_payload.get("display") or display_formula,
                "expression": expression or "",
                "groups": groups or [],
                "modifier": modifier or 0,
                "total": total if total is not None else "",
                "kind": metadata.get("intent") or "roll",
                "visibility": metadata.get("visibility") or "public",
            },
            "input": metadata.get("rollInput") if isinstance(metadata.get("rollInput"), dict) else {},
        }

    def _render_chat_card(self, *, system_id: str, card_id: Any, context: dict) -> dict | None:
        if not isinstance(card_id, str) or not card_id:
            return None
        mappings = self.rules.get_chat_card_mappings(system_id)
        cards = mappings.get("cards") if isinstance(mappings.get("cards"), dict) else mappings
        spec = cards.get(card_id) if isinstance(cards, dict) else None
        if not isinstance(spec, dict):
            return None
        title = self._resolve(spec.get("title", "@action.label"), context)
        subtitle = self._resolve(spec.get("subtitle", ""), context)
        lines = []
        raw_lines = spec.get("lines")
        if isinstance(raw_lines, list):
            for line in raw_lines[:12]:
                if not isinstance(line, dict):
                    continue
                label = self._resolve(line.get("label", ""), context)
                value = self._resolve(line.get("value", ""), context)
                if value in (None, ""):
                    continue
                lines.append({"label": str(label or ""), "value": str(value)})
        return {
            "id": card_id,
            "title": str(title or ""),
            "subtitle": str(subtitle or ""),
            "lines": lines,
            "total": context["roll"]["total"],
        }

    def _render_roll_toast(self, *, system_id: str, toast_id: Any, context: dict) -> dict | None:
        if not isinstance(toast_id, str) or not toast_id:
            return None
        mappings = self.rules.get_roll_toast_mappings(system_id)
        toasts = mappings.get("toasts") if isinstance(mappings.get("toasts"), dict) else mappings
        spec = toasts.get(toast_id) if isinstance(toasts, dict) else None
        if not isinstance(spec, dict):
            return None
        return {
            "id": toast_id,
            "title": str(self._resolve(spec.get("title", "@action.label"), context) or ""),
            "subtitle": str(self._resolve(spec.get("subtitle", ""), context) or ""),
            "formula": str(self._resolve(spec.get("formula", "@roll.formula"), context) or ""),
            "total": self._resolve(spec.get("total", "@roll.total"), context),
            "kind": str(self._resolve(spec.get("kind", "@roll.kind"), context) or "roll"),
        }

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

    def _fallback_toast(self, *, label: str | None, expression: str | None, total: int | None) -> dict:
        return {
            "id": "default",
            "title": label or "Roll",
            "subtitle": expression or "",
            "formula": expression or "",
            "total": total if total is not None else "",
            "kind": "roll",
        }
