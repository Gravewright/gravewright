"""Lightweight validation/normalization of the declarative Sheet IR (§8).

The renderer is tolerant (unknown nodes render nothing), but we still sanity
-check a layout before handing it to the client: it must be an ``actorSheet``
with a ``body``, and every node's ``type`` must be in the v0 component set.
"""

from __future__ import annotations

LAYOUT_TYPES = {"tabs", "tab", "section", "row", "column", "grid", "divider", "spacer"}
FIELD_TYPES = {
    "textField",
    "textArea",
    "numberField",
    "checkboxField",
    "checkboxTrack",
    "selectField",
    "resourceField",
    "imageField",
    "readonlyField",
    "modifierBuilder",
}
ACTION_TYPES = {"rollButton", "actionButton", "incrementButton", "decrementButton"}
DISPLAY_TYPES = {"text", "badge", "resourceBar", "itemList", "dropZone", "abilityCard", "combatStat", "resourceBox", "rollableStat"}

KNOWN_TYPES = LAYOUT_TYPES | FIELD_TYPES | ACTION_TYPES | DISPLAY_TYPES

_DIALOG_FIELD_TYPES = {"boolean", "number", "text", "select", "segmented", "radio", "dice", "diceList", "formula", "visibility", "separator", "hint"}
_ITEM_ROW_TYPES = {"weaponRow", "spellRow", "featureRow", "inventoryRow", "effectRow"}
_ITEM_ROW_ACTION_TYPES = {"itemAction", "openEmbeddedItemAction", "removeAction"}


def _validate_roll_dialog(value: object, errors: list[str]) -> None:
    if value in (None, "roll"):
        return
    if not isinstance(value, dict):
        errors.append("game.sheet_ir.errors.interaction_item_dialog")
        return
    fields = value.get("fields")
    if not isinstance(fields, list) or not fields:
        errors.append("game.sheet_ir.errors.roll_dialog_fields")
        return
    for field in fields:
        if not isinstance(field, dict):
            errors.append("game.sheet_ir.errors.roll_dialog_field_invalid")
            continue
        field_type = field.get("type")
        if field_type not in _DIALOG_FIELD_TYPES:
            errors.append("game.sheet_ir.errors.roll_dialog_field_type")
        if field_type not in {"separator", "hint"}:
            if not isinstance(field.get("id"), str) or not field.get("id"):
                errors.append("game.sheet_ir.errors.roll_dialog_field_id")
        if field_type in {"select", "segmented", "radio"}:
            options = field.get("options")
            if not isinstance(options, list) or not options:
                errors.append("game.sheet_ir.errors.roll_dialog_select_options")


def _validate_modifier_builder(node: dict, errors: list[str]) -> None:
    if not isinstance(node.get("path"), str) or not node.get("path"):
        errors.append("game.sheet_ir.errors.modifier_builder_path")
    targets = node.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("game.sheet_ir.errors.modifier_builder_targets")
        return
    for target in targets[:128]:
        if not isinstance(target, dict):
            errors.append("game.sheet_ir.errors.modifier_builder_target_invalid")
            continue
        if not isinstance(target.get("id"), str) or not target.get("id"):
            errors.append("game.sheet_ir.errors.modifier_builder_target_id")
        operations = target.get("operations")
        if not isinstance(operations, list) or not operations:
            errors.append("game.sheet_ir.errors.modifier_builder_operations")
            continue
        for op in operations[:32]:
            if not isinstance(op, dict):
                errors.append("game.sheet_ir.errors.modifier_builder_operation_invalid")
                continue
            if not isinstance(op.get("id"), str) or not op.get("id"):
                errors.append("game.sheet_ir.errors.modifier_builder_operation_id")


def _validate_item_row(value: object, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append("game.sheet_ir.errors.item_row_invalid")
        return
    row_type = value.get("type")
    if row_type is not None and row_type not in _ITEM_ROW_TYPES:
        errors.append("game.sheet_ir.errors.item_row_type")
    actions = value.get("actions")
    if actions is None:
        return
    if not isinstance(actions, list):
        errors.append("game.sheet_ir.errors.item_row_actions")
        return
    for action in actions:
        if not isinstance(action, dict):
            errors.append("game.sheet_ir.errors.item_row_action_invalid")
            continue
        action_type = action.get("type")
        if action_type not in _ITEM_ROW_ACTION_TYPES:
            errors.append("game.sheet_ir.errors.item_row_action_type")
            continue
        if action_type == "itemAction" and (not isinstance(action.get("action"), str) or not action.get("action")):
            errors.append("game.sheet_ir.errors.item_row_action_target")
        if "dialog" in action:
            _validate_roll_dialog(action.get("dialog"), errors)


def _validate_interaction(value: object, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append("game.sheet_ir.errors.interaction_invalid")
        return
    kind = value.get("type")
    if kind == "action":
        if not isinstance(value.get("action"), str) or not value.get("action"):
            errors.append("game.sheet_ir.errors.interaction_action")
        if "dialog" in value:
            _validate_roll_dialog(value.get("dialog"), errors)
        return
    if kind == "actionMenu":
        items = value.get("items")
        if not isinstance(items, list) or not items:
            errors.append("game.sheet_ir.errors.interaction_items")
            return
        for item in items:
            if not isinstance(item, dict):
                errors.append("game.sheet_ir.errors.interaction_item_invalid")
                continue
            label = item.get("label")
            label_key = item.get("labelKey")
            if not (isinstance(label, str) and label) and not (isinstance(label_key, str) and label_key):
                errors.append("game.sheet_ir.errors.interaction_item_label")
            has_action = isinstance(item.get("action"), str) and bool(item.get("action"))
            has_command = isinstance(item.get("command"), str) and bool(item.get("command"))
            if not has_action and not has_command:
                errors.append("game.sheet_ir.errors.interaction_item_target")
            if "dialog" in item:
                _validate_roll_dialog(item.get("dialog"), errors)
        return
    errors.append("game.sheet_ir.errors.interaction_type")


def _walk(node: object, errors: list[str], depth: int = 0) -> None:
    if depth > 40:
        errors.append("game.sheet_ir.errors.too_deep")
        return
    if isinstance(node, list):
        for item in node:
            _walk(item, errors, depth + 1)
        return
    if not isinstance(node, dict):
        return
    node_type = node.get("type")
    if node_type is not None and node_type not in KNOWN_TYPES:
        errors.append("game.sheet_ir.errors.unknown_component")
    if node_type == "abilityCard":
        if not isinstance(node.get("scorePath"), str) or not node.get("scorePath"):
            errors.append("game.sheet_ir.errors.ability_card_score_path")
        if not isinstance(node.get("modPath"), str) or not node.get("modPath"):
            errors.append("game.sheet_ir.errors.ability_card_mod_path")
        if "rollAction" in node and node.get("rollAction") is not None and not isinstance(node.get("rollAction"), str):
            errors.append("game.sheet_ir.errors.ability_card_roll_action")
        _validate_interaction(node.get("interaction"), errors)
    if node_type == "combatStat":
        if not isinstance(node.get("valuePath"), str) or not node.get("valuePath"):
            errors.append("game.sheet_ir.errors.combat_stat_value_path")
        if "rollAction" in node and node.get("rollAction") is not None and not isinstance(node.get("rollAction"), str):
            errors.append("game.sheet_ir.errors.combat_stat_roll_action")
        _validate_interaction(node.get("interaction"), errors)
    if node_type == "rollableStat":
                                                                             
                                                   
        if node.get("interaction") is None and not node.get("rollAction"):
            errors.append("game.sheet_ir.errors.interaction_action")
        _validate_interaction(node.get("interaction"), errors)
    if node_type == "resourceBox":
        if not isinstance(node.get("valuePath"), str) or not node.get("valuePath"):
            errors.append("game.sheet_ir.errors.resource_box_value_path")
        if not isinstance(node.get("maxPath"), str) or not node.get("maxPath"):
            errors.append("game.sheet_ir.errors.resource_box_max_path")
    if node_type == "modifierBuilder":
        _validate_modifier_builder(node, errors)
    if node_type == "itemList":
        _validate_item_row(node.get("row"), errors)
    for key in ("children", "tabs"):
        if key in node:
            _walk(node[key], errors, depth + 1)


def find_drop_zone(layout: object, zone_id: str) -> dict | None:
    """Locate a dropZone (standalone or nested in an itemList) by id.

    Returns ``{"accepts": [...], "onDrop": "..."}`` or None.
    """
    if not isinstance(layout, dict) or not zone_id:
        return None
    stack: list[object] = [layout.get("body")]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        if node.get("type") == "dropZone" and node.get("id") == zone_id:
            return {"accepts": node.get("accepts") or [], "onDrop": node.get("onDrop", "")}
        nested = node.get("dropZone")
        if isinstance(nested, dict) and nested.get("id") == zone_id:
            return {"accepts": nested.get("accepts") or [], "onDrop": nested.get("onDrop", "")}
        for key in ("children", "tabs"):
            if key in node:
                stack.append(node[key])
    return None


def list_drop_zones(layout: object) -> list[dict]:
    """Every dropZone in the layout (standalone or nested in an itemList), in
    document order. Used to route a sheet-wide drop to the zone whose ``accepts``
    matches the dropped entry (Foundry-style "drop anywhere on the sheet")."""
    zones: list[dict] = []
    if not isinstance(layout, dict):
        return zones

    def visit(node: object) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child)
            return
        if not isinstance(node, dict):
            return
        if node.get("type") == "dropZone":
            zones.append(
                {"id": node.get("id", ""), "accepts": node.get("accepts") or [], "onDrop": node.get("onDrop", "")}
            )
        nested = node.get("dropZone")
        if isinstance(nested, dict):
            zones.append(
                {"id": nested.get("id", ""), "accepts": nested.get("accepts") or [], "onDrop": nested.get("onDrop", "")}
            )
        for key in ("children", "tabs"):
            if key in node:
                visit(node[key])

    visit(layout.get("body"))
    return zones


def find_matching_drop_zone(layout: object, entry_type: str) -> dict | None:
    """First dropZone whose ``accepts`` matches ``entry_type`` (document order)."""
    for zone in list_drop_zones(layout):
        if accepts_entry(zone["accepts"], entry_type):
            return zone
    return None


def accepts_entry(accepts: list, entry_type: str) -> bool:
    """A zone accepts an entry if a token equals the canonical dropType or
    either side's suffix (``item.weapon`` ~ ``weapon``, ``effect.condition`` ~
    ``condition``)."""
    if not entry_type:
        return False
    entry = str(entry_type)
    entry_suffix = entry.split(".")[-1]
    for token in accepts:
        if not isinstance(token, str):
            continue
        token_suffix = token.split(".")[-1]
        if token == entry or token == entry_suffix or token_suffix == entry or token_suffix == entry_suffix:
            return True
    return False


def validate_sheet_ir(ir: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(ir, dict):
        return ["game.sheet_ir.errors.not_object"]
    if ir.get("kind") not in {"actorSheet", "itemSheet"}:
        errors.append("game.sheet_ir.errors.kind")
    if not isinstance(ir.get("body"), dict):
        errors.append("game.sheet_ir.errors.body_required")
    else:
        _walk(ir["body"], errors)
                                          
    seen: set[str] = set()
    unique: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            unique.append(error)
    return unique
