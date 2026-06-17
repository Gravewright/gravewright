from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import config
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sdk.package_locale_service import PackageLocaleService


DEFAULT_ACTIVITY_TYPES = [
    {"id": "token.move", "label": "Mover token"},
    {"id": "sheet.action", "label": "Usar ação da ficha"},
    {"id": "sheet.item.action", "label": "Usar item"},
]

DEFAULT_INITIATIVE = {
    "mode": "manual",
    "label": "Ordem Manual",
    "roll": {"actionId": "roll.initiative"},
    "sort": {"direction": "desc", "tieBreakers": []},
    "allowReroll": True,
    "allowManualEdit": True,
}

DEFAULT_COMBAT_UI = {
    "combat": {
        "skin": "default",
        "density": "compact",
        "palette": {
            "accent": "#c09a5a",
            "accentStrong": "#f8e5ad",
            "danger": "#ef4444",
            "dangerSoft": "#fca5a5",
            "current": "#28d17c",
            "next": "#ef4444",
            "acted": "#9ca3af",
            "scrollbarThumb": "#c09a5a",
            "scrollbarTrack": "#080a0d",
        },
        "initiative": {
            "icon": "ph-dice-five",
            "monsterIcon": "ph-skull",
            "rollAllLabel": "Rolar todas",
            "rollMonstersLabel": "Só monstros",
            "rollSubtitle": "d20 + mod.",
            "monsterSubtitle": "NPCs e criaturas",
        },
        "statusLabels": {
            "current": "Turno atual",
            "next": "Próximo",
            "acted": "Já agiu",
            "waiting": "Aguardando",
        },
    }
}


@dataclass(frozen=True)
class CombatConfig:
    system_id: str = ""
    default_mode: str = "manual"
    turn_order: dict = field(default_factory=lambda: {"strategy": "manual", "label": "Ordem Manual"})
    initiative: dict = field(default_factory=lambda: dict(DEFAULT_INITIATIVE))
    resources: dict = field(default_factory=dict)
    ui: dict = field(default_factory=lambda: _deep_copy_dict(DEFAULT_COMBAT_UI))
    activity_types: list[dict] = field(default_factory=lambda: list(DEFAULT_ACTIVITY_TYPES))

    @property
    def strategy(self) -> str:
        strategy = self.turn_order.get("strategy") if isinstance(self.turn_order, dict) else "manual"
        return str(strategy or _strategy_for_initiative(self.initiative))

    def payload(self) -> dict:
        return {
            "systemId": self.system_id,
            "defaultMode": self.default_mode,
            "turnOrder": self.turn_order,
            "initiative": self.initiative,
            "resources": self.resources,
            "ui": self.ui,
            "activityTypes": self.activity_types,
        }


class CombatConfigService:
    """Loads a system-authored combat configuration.

    ``rules/combat.gw.json`` exposes both behavior and presentation contracts:
    ``initiative`` defines how order is produced, while ``ui.combat`` defines
    labels, icons, palette and skin classes for the combat panel. ``turnOrder``
    carries the turn-order strategy/groups; ``initiative`` defines the mode,
    roll formula/action, sorting, tie-breakers and appearance in one place.
    """

    def __init__(self) -> None:
        self.rules = SystemRulesService()
        self.locales = PackageLocaleService()

    def get_for_system(self, system_id: str | None) -> CombatConfig:
        if not system_id:
            return CombatConfig()
        raw = self.rules.get_combat_config(system_id)
        if not isinstance(raw, dict):
            raw = {}
        catalog = self.locales.get_locale(system_id, config.default_locale)
        if catalog:
            raw = _localize_keys(raw, catalog)
        raw_turn_order = raw.get("turnOrder") if isinstance(raw.get("turnOrder"), dict) else {}
        initiative = _normalize_initiative(raw.get("initiative"), raw_turn_order)
        ui = _normalize_ui(raw.get("ui"), initiative=initiative)
        turn_order = dict(raw_turn_order) if raw_turn_order else _turn_order_from_initiative(initiative)
        if not turn_order:
            turn_order = {"strategy": "manual", "label": "Ordem Manual", "allowDragReorder": True}
        resources = raw.get("resources") if isinstance(raw.get("resources"), dict) else {}
        activity_types = raw.get("activityTypes") if isinstance(raw.get("activityTypes"), list) else list(DEFAULT_ACTIVITY_TYPES)
        return CombatConfig(
            system_id=system_id,
            default_mode=str(raw.get("defaultMode") or initiative.get("mode") or turn_order.get("strategy") or "manual"),
            turn_order=turn_order,
            initiative=initiative,
            resources=resources,
            ui=ui,
            activity_types=[item for item in activity_types if isinstance(item, dict)],
        )


def _localize_keys(value: Any, catalog: dict[str, str]) -> Any:
    """Resolve system locale keys that appear as literal values in the config.

    ``combat.gw.json`` places catalog keys (e.g. ``"<pkg>.ui.initiative.label"``)
    directly in label positions. Catalog keys are namespaced, so plain literal
    labels never collide and pass through untouched.
    """
    if isinstance(value, dict):
        return {key: _localize_keys(item, catalog) for key, item in value.items()}
    if isinstance(value, list):
        return [_localize_keys(item, catalog) for item in value]
    if isinstance(value, str):
        return catalog.get(value, value)
    return value


def supported_strategies() -> set[str]:
    return {
        "formula_sort",
        "group_formula_sort",
        "deck_draw",
        "manual",
        "spotlight",
        "alternating_sides",
    }


def supported_initiative_modes() -> set[str]:
    return {"individual", "side", "deck", "manual", "spotlight", "alternating_sides"}


def _normalize_initiative(raw: Any, turn_order: dict) -> dict:
    initiative = dict(raw) if isinstance(raw, dict) else {}
    mode = _initiative_mode(str(initiative.get("mode") or ""), turn_order)
    label = str(initiative.get("label") or turn_order.get("label") or "Iniciativa")

    roll = initiative.get("roll") if isinstance(initiative.get("roll"), dict) else {}
    roll = dict(roll)
    if initiative.get("rollActionId") and not roll.get("actionId"):
        roll["actionId"] = initiative.get("rollActionId")
    if initiative.get("formula") and not roll.get("formula"):
        roll["formula"] = initiative.get("formula")
    if not roll:
        roll = {"actionId": "roll.initiative"}

    sort = _normalize_sort(
        initiative.get("sort"),
        fallback_direction=initiative.get("sortDirection") or turn_order.get("sort") or "desc",
        fallback_tie_breakers=initiative.get("tieBreakers") or turn_order.get("tieBreakers") or [],
    )

    normalized = {
        "mode": mode,
        "label": label,
        "roll": roll,
        "sort": sort,
        "allowReroll": bool(initiative.get("allowReroll", True)),
        "allowManualEdit": bool(initiative.get("allowManualEdit", True)),
    }
    if isinstance(initiative.get("appearance"), dict):
        normalized["appearance"] = _normalize_appearance(initiative["appearance"])
    if isinstance(initiative.get("groups"), list):
        normalized["groups"] = initiative["groups"]
    elif isinstance(turn_order.get("groups"), list):
        normalized["groups"] = turn_order["groups"]
    if isinstance(initiative.get("deck"), dict):
        normalized["deck"] = initiative["deck"]
    elif isinstance(turn_order.get("deck"), dict):
        normalized["deck"] = turn_order["deck"]
    if isinstance(initiative.get("manual"), dict):
        normalized["manual"] = initiative["manual"]
    elif turn_order.get("allowDragReorder") is not None:
        normalized["manual"] = {"allowDragReorder": bool(turn_order.get("allowDragReorder"))}
    return normalized


def _normalize_ui(raw: Any, *, initiative: dict) -> dict:
    """Normalize the system-authored combat UI contract.

    The payload is deliberately data-only. Frontend code maps the sanitized
    ``skin`` and CSS custom properties into the actual rendering so a system can
    theme combat without shipping arbitrary runtime CSS/JS.
    """
    defaults = _deep_copy_dict(DEFAULT_COMBAT_UI)
    raw_ui = raw if isinstance(raw, dict) else {}
    combat = raw_ui.get("combat") if isinstance(raw_ui.get("combat"), dict) else raw_ui
    combat = combat if isinstance(combat, dict) else {}
    default_combat = defaults["combat"]

    appearance = initiative.get("appearance") if isinstance(initiative.get("appearance"), dict) else {}

    normalized_combat: dict[str, Any] = {
        "skin": _safe_token(combat.get("skin") or combat.get("theme") or appearance.get("theme") or default_combat["skin"]),
        "density": _safe_token(combat.get("density") or default_combat["density"]),
        "palette": _normalize_palette(combat.get("palette"), fallback=default_combat["palette"]),
        "initiative": _normalize_ui_initiative(combat.get("initiative"), initiative=initiative, appearance=appearance),
        "statusLabels": _normalize_status_labels(combat.get("statusLabels"), fallback=default_combat["statusLabels"]),
    }
    if isinstance(combat.get("hero"), dict):
        normalized_combat["hero"] = _normalize_small_string_dict(combat["hero"])
    if isinstance(combat.get("participant"), dict):
        normalized_combat["participant"] = _normalize_small_string_dict(combat["participant"])
    return {"combat": normalized_combat}


def _normalize_ui_initiative(raw: Any, *, initiative: dict, appearance: dict) -> dict:
    raw_initiative = raw if isinstance(raw, dict) else {}
    defaults = DEFAULT_COMBAT_UI["combat"]["initiative"]
    return {
        "icon": _safe_icon(raw_initiative.get("icon") or appearance.get("icon") or defaults["icon"]),
        "monsterIcon": _safe_icon(raw_initiative.get("monsterIcon") or appearance.get("monsterIcon") or defaults["monsterIcon"]),
        "rollAllLabel": _safe_label(raw_initiative.get("rollAllLabel") or appearance.get("rollAllLabel") or defaults["rollAllLabel"]),
        "rollMonstersLabel": _safe_label(raw_initiative.get("rollMonstersLabel") or appearance.get("rollMonstersLabel") or defaults["rollMonstersLabel"]),
        "rollSubtitle": _safe_label(raw_initiative.get("rollSubtitle") or appearance.get("rollSubtitle") or defaults["rollSubtitle"]),
        "monsterSubtitle": _safe_label(raw_initiative.get("monsterSubtitle") or appearance.get("monsterSubtitle") or defaults["monsterSubtitle"]),
        "scoreLabel": _safe_label(raw_initiative.get("scoreLabel") or initiative.get("label") or "Iniciativa"),
    }


def _normalize_appearance(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("theme", "die", "rollAllLabel", "rollMonstersLabel", "rollSubtitle", "monsterSubtitle", "accent"):
        value = raw.get(key)
        if value is not None:
            out[key] = _safe_label(value) if "Label" in key or "Subtitle" in key else _safe_token(value)
    if raw.get("icon"):
        out["icon"] = _safe_icon(raw.get("icon"))
    if raw.get("monsterIcon"):
        out["monsterIcon"] = _safe_icon(raw.get("monsterIcon"))
    if raw.get("die"):
        out["die"] = _safe_label(raw.get("die"))
    return out


def _normalize_palette(raw: Any, *, fallback: dict) -> dict:
    palette = dict(fallback)
    if not isinstance(raw, dict):
        return palette
    allowed = set(fallback) | {"surface", "surfaceRaised", "text", "muted", "border", "gold", "blood"}
    key_aliases = {
        "accent-strong": "accentStrong",
        "accentstrong": "accentStrong",
        "danger-soft": "dangerSoft",
        "dangersoft": "dangerSoft",
        "scrollbar-thumb": "scrollbarThumb",
        "scrollbarthumb": "scrollbarThumb",
        "scrollbar-track": "scrollbarTrack",
        "scrollbartrack": "scrollbarTrack",
        "surface-raised": "surfaceRaised",
        "surfaceraised": "surfaceRaised",
    }
    canonical = { _safe_token(key): key for key in allowed }
    for key, value in raw.items():
        clean_key = _safe_token(key)
        normalized_key = key_aliases.get(clean_key, canonical.get(clean_key, clean_key))
        if normalized_key not in allowed:
            continue
        clean_value = _safe_color(value)
        if clean_value:
            palette[normalized_key] = clean_value
    return palette


def _normalize_status_labels(raw: Any, *, fallback: dict) -> dict:
    labels = dict(fallback)
    if not isinstance(raw, dict):
        return labels
    for key in ("current", "next", "acted", "waiting"):
        if raw.get(key):
            labels[key] = _safe_label(raw[key])
    return labels


def _normalize_small_string_dict(raw: dict) -> dict:
    out: dict[str, str] = {}
    for key, value in raw.items():
        clean_key = _safe_token(key)
        if clean_key:
            out[clean_key] = _safe_label(value)
    return out


def _safe_label(value: Any, *, limit: int = 80) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _safe_token(value: Any, *, fallback: str = "default") -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    clean = "".join(ch for ch in text if ch.isalnum() or ch == "-")[:40].strip("-")
    return clean or fallback


def _safe_icon(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text.startswith("ph-"):
        text = f"ph-{text}" if text else "ph-dice-five"
    clean = "".join(ch for ch in text if ch.isalnum() or ch == "-")[:48]
    return clean if clean.startswith("ph-") else "ph-dice-five"


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


def _deep_copy_dict(value: dict) -> dict:
    out: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            out[key] = _deep_copy_dict(item)
        elif isinstance(item, list):
            out[key] = list(item)
        else:
            out[key] = item
    return out


def _normalize_sort(raw: Any, *, fallback_direction: Any, fallback_tie_breakers: Any) -> dict:
    sort = dict(raw) if isinstance(raw, dict) else {}
    direction = str(sort.get("direction") or sort.get("order") or fallback_direction or "desc").lower()
    if direction in {"descending", "highest", "high_to_low"}:
        direction = "desc"
    elif direction in {"ascending", "lowest", "low_to_low", "low_to_high"}:
        direction = "asc"
    elif direction not in {"asc", "desc"}:
        direction = "desc"
    tie_breakers = sort.get("tieBreakers", fallback_tie_breakers)
    if not isinstance(tie_breakers, list):
        tie_breakers = []
    return {"direction": direction, "tieBreakers": [str(item) for item in tie_breakers[:8]]}


def _initiative_mode(raw_mode: str, turn_order: dict) -> str:
    raw_mode = raw_mode.lower()
    aliases = {
        "individual_initiative": "individual",
        "formula": "individual",
        "formula_sort": "individual",
        "group": "side",
        "group_formula_sort": "side",
        "side_formula": "side",
        "deck_draw": "deck",
        "cards": "deck",
        "manual": "manual",
        "spotlight": "spotlight",
        "alternating": "alternating_sides",
        "alternating_sides": "alternating_sides",
    }
    if raw_mode in aliases:
        return aliases[raw_mode]
    strategy = str(turn_order.get("strategy") or "manual")
    return _mode_for_strategy(strategy)


def _mode_for_strategy(strategy: str) -> str:
    return {
        "formula_sort": "individual",
        "group_formula_sort": "side",
        "deck_draw": "deck",
        "spotlight": "spotlight",
        "alternating_sides": "alternating_sides",
    }.get(strategy, "manual")


def _strategy_for_mode(mode: str) -> str:
    return {
        "individual": "formula_sort",
        "side": "group_formula_sort",
        "deck": "deck_draw",
        "spotlight": "spotlight",
        "alternating_sides": "alternating_sides",
    }.get(mode, "manual")


def _strategy_for_initiative(initiative: dict) -> str:
    return _strategy_for_mode(str(initiative.get("mode") or "manual"))


def _turn_order_from_initiative(initiative: dict) -> dict:
    mode = str(initiative.get("mode") or "manual")
    roll = initiative.get("roll") if isinstance(initiative.get("roll"), dict) else {}
    sort = initiative.get("sort") if isinstance(initiative.get("sort"), dict) else {}
    out = {
        "strategy": _strategy_for_mode(mode),
        "label": initiative.get("label") or "Iniciativa",
        "sort": sort.get("direction") or "desc",
        "tieBreakers": sort.get("tieBreakers") or [],
    }
    if roll.get("formula"):
        out["formula"] = roll.get("formula")
    if mode == "manual":
        out["allowDragReorder"] = bool((initiative.get("manual") or {}).get("allowDragReorder", True)) if isinstance(initiative.get("manual"), dict) else True
    if isinstance(initiative.get("groups"), list):
        out["groups"] = initiative["groups"]
    if isinstance(initiative.get("deck"), dict):
        out["deck"] = initiative["deck"]
    return out
