from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import config
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sdk.package_locale_service import PackageLocaleService

DEFAULT_ACTION_ID = "roll.initiative"
DEFAULT_ICON = "ph-dice-five"







INPUTS = {"roll", "number", "text"}
SORTS = {"desc", "asc"}


@dataclass(frozen=True)
class CombatConfig:
    """What the active system says about initiative, and nothing else.

    The core owns the encounter, the turn order and the panel. A system answers
    three questions: what initiative is called, how a value is produced, and
    which resource bar to draw. It is never asked what initiative *means* — the
    stored value is opaque text, so a system that tracks cards, phases or plain
    words is as native as one that rolls a die.
    """

    system_id: str = ""
    label: str = "Initiative"
    input: str = "number"
    sort: str = "desc"
    formula: str = ""
    action_id: str = DEFAULT_ACTION_ID
    tie_breaker: str = ""
    icon: str = DEFAULT_ICON
    accent: str = ""
    resources: dict = field(default_factory=dict)

    @property
    def is_numeric(self) -> bool:
        """Whether the core may read the value as a number for ordering."""
        return self.input in {"roll", "number"}

    @property
    def is_manual_order(self) -> bool:
        """Whether the GM arranges the order by hand instead of by value."""
        return not self.is_numeric

    def payload(self) -> dict:
        return {
            "system_id": self.system_id,
            "label": self.label,
            "input": self.input,
            "sort": self.sort,
            "manual_order": self.is_manual_order,
            "icon": self.icon,
            "accent": self.accent,
            "resources": self.resources,
        }


class CombatConfigService:
    """Reads ``rules/combat.gw.json`` from the campaign's active system."""

    def __init__(self) -> None:
        self.rules = SystemRulesService()
        self.locales = PackageLocaleService()

    def get_for_system(self, system_id: str | None) -> CombatConfig:
        if not system_id:
            return CombatConfig()
        raw = self.rules.get_combat_config(system_id)
        if not isinstance(raw, dict):
            return CombatConfig(system_id=system_id)
        initiative = _initiative_section(raw)
        catalog = self.locales.get_locale(system_id, config.default_locale)
        label = str(initiative.get("label") or "Initiative")
        formula = _safe_formula(initiative.get("formula"))
        return CombatConfig(
            system_id=system_id,
            label=_safe_label(catalog.get(label, label) if catalog else label) or "Initiative",
            input=_input(initiative.get("input"), formula=formula),
            sort=_sort(initiative.get("sort")),
            formula=formula,
            action_id=_safe_token(initiative.get("actionId"), fallback=DEFAULT_ACTION_ID),
            tie_breaker=_safe_path(initiative.get("tieBreaker")),
            icon=_safe_icon(initiative.get("icon")),
            accent=_safe_color(initiative.get("accent")) or "",
            resources=raw.get("resources") if isinstance(raw.get("resources"), dict) else {},
        )


def _input(raw: Any, *, formula: str) -> str:
    """Pick the entry mode, defaulting to what the rest of the config implies."""
    value = str(raw or "").strip().lower()
    if value in INPUTS:
        return value
    return "roll" if formula else "number"


def _sort(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    aliases = {"descending": "desc", "highest": "desc", "ascending": "asc", "lowest": "asc"}
    return aliases.get(value, value if value in SORTS else "desc")


def _initiative_section(raw: dict) -> dict:
    """Flatten the authored initiative block, accepting the pre-v2 nesting.

    Packages written against the old contract nested the formula under
    ``initiative.roll`` and the tie-breaker under ``initiative.sort.tieBreakers``,
    or put both on ``turnOrder``. Their ``mode`` also carried the entry style:
    everything that was not a per-combatant formula (card draws, spotlight,
    alternating sides, plain manual order) is a hand-arranged order now.
    """
    initiative = raw.get("initiative") if isinstance(raw.get("initiative"), dict) else {}
    turn_order = raw.get("turnOrder") if isinstance(raw.get("turnOrder"), dict) else {}
    roll = initiative.get("roll") if isinstance(initiative.get("roll"), dict) else {}
    appearance = (
        initiative.get("appearance") if isinstance(initiative.get("appearance"), dict) else {}
    )

    raw_sort = initiative.get("sort")
    sort_block = raw_sort if isinstance(raw_sort, dict) else {}
    tie_breakers = sort_block.get("tieBreakers") or turn_order.get("tieBreakers") or []
    legacy_mode = str(initiative.get("mode") or turn_order.get("strategy") or "").lower()
    return {
        "label": initiative.get("label") or turn_order.get("label"),
        "input": initiative.get("input") or _input_for_legacy_mode(legacy_mode),
        "sort": raw_sort
        if isinstance(raw_sort, str)
        else (sort_block.get("direction") or turn_order.get("sort")),
        "formula": initiative.get("formula") or roll.get("formula") or turn_order.get("formula"),
        "actionId": initiative.get("actionId") or roll.get("actionId"),
        "tieBreaker": initiative.get("tieBreaker")
        or (tie_breakers[0] if isinstance(tie_breakers, list) and tie_breakers else ""),
        "icon": initiative.get("icon") or appearance.get("icon"),
        "accent": initiative.get("accent") or appearance.get("accent"),
    }


def _input_for_legacy_mode(mode: str) -> str:
    if not mode:
        return ""
    hand_arranged = {
        "manual",
        "deck",
        "deck_draw",
        "cards",
        "spotlight",
        "alternating",
        "alternating_sides",
    }
    return "text" if mode in hand_arranged else ""


def _safe_label(value: Any, *, limit: int = 40) -> str:
    return str(value or "").strip()[:limit]


def _safe_formula(value: Any) -> str:
    return str(value or "").strip()[:200]


def _safe_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text.startswith("@"):
        return ""
    clean = "".join(ch for ch in text[1:] if ch.isalnum() or ch in "._")[:80]
    return f"@{clean}" if clean else ""


def _safe_token(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    clean = "".join(ch for ch in text if ch.isalnum() or ch in ".-_")[:48]
    return clean or fallback


def _safe_icon(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return DEFAULT_ICON
    if not text.startswith("ph-"):
        text = f"ph-{text}"
    clean = "".join(ch for ch in text if ch.isalnum() or ch == "-")[:48]
    return clean if clean.startswith("ph-") else DEFAULT_ICON


def _safe_color(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text.startswith("#"):
        return None
    hex_part = text[1:]
    if len(hex_part) not in {3, 4, 6, 8}:
        return None
    if not all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
        return None
    return f"#{hex_part}"
