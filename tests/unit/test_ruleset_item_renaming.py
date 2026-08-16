"""Item sheets must edit Item Core identity rather than duplicate the name in sheet data."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ITEM_RENDERER = ROOT / "static/js/sheets/items/item-sheet-renderer.js"
ITEM_CONTROLLER = ROOT / "static/js/sheets/items/item-sheet-controller.js"


def test_item_name_uses_the_sdk_write_path_and_reconciles_the_modal_title():
    controller = ITEM_CONTROLLER.read_text(encoding="utf-8")
    renderer = ITEM_RENDERER.read_text(encoding="utf-8")

    core_write = controller.split('if (path === "core.name")', 1)[1].split("}", 1)[0]
    assert 'postJSON("/game/item/update-core"' in core_write
    assert "item_id: meta.itemId" in core_write

    refresh = renderer.split("async function refresh(root)", 1)[1].split(
        "\n  FI.contexts", 1
    )[0]
    assert 'querySelector(".sheet-modal-name")' in refresh
    assert "modalTitle.textContent = bundle.item.name" in refresh