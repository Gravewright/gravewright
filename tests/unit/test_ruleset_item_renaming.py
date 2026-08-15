"""Item sheets must edit Item Core identity rather than duplicate the name in sheet data."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RULESETS = ROOT / "data/packages/rulesets"
ITEM_RENDERER = ROOT / "static/js/sheets/items/item-sheet-renderer.js"
ITEM_CONTROLLER = ROOT / "static/js/sheets/items/item-sheet-controller.js"


def _item_layouts(system_id: str) -> list[Path]:
    return sorted((RULESETS / system_id / "layouts/items").glob("*.sheet.gw.json"))


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_dnd5e_and_savage_worlds_item_sheets_expose_the_canonical_name():
    for system_id in ("dnd5e", "savage-worlds"):
        layouts = _item_layouts(system_id)
        assert layouts, f"{system_id} has no item sheets"
        for layout_path in layouts:
            layout = json.loads(layout_path.read_text(encoding="utf-8"))
            name_fields = [
                node
                for node in _walk(layout.get("body"))
                if node.get("type") == "textField" and node.get("path") == "core.name"
            ]
            assert len(name_fields) == 1, (
                f"{layout_path.name} must expose exactly one editable core.name field"
            )


def test_item_name_uses_the_sdk_write_path_and_reconciles_the_modal_title():
    controller = ITEM_CONTROLLER.read_text(encoding="utf-8")
    renderer = ITEM_RENDERER.read_text(encoding="utf-8")

    core_write = controller.split('if (path === "core.name")', 1)[1].split("}", 1)[0]
    assert 'postJSON("/game/item/update-core"' in core_write
    assert "item_id: meta.itemId" in core_write

    refresh = renderer.split("async function refresh(root)", 1)[1].split("\n  FI.contexts", 1)[0]
    assert 'querySelector(".sheet-modal-name")' in refresh
    assert "modalTitle.textContent = bundle.item.name" in refresh
