from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_resource_panels_reconcile_after_socket_reconnect():
    expected = {
        "static/js/actors/actors-panel.js": "refreshPanel(panel.dataset.roomId)",
        "static/js/items/items-panel.js": "refreshPanel(panel.dataset.roomId)",
        "static/js/journals/journals-panel.js": "refreshJournalPanel(panel.dataset.roomId)",
        "static/js/assets/asset-library.js": "controllers.forEach((controller) => controller.refresh())",
    }
    for path, refresh in expected.items():
        script = source(path)
        assert 'addEventListener("vtt:ws-open"' in script, path
        assert refresh in script, path


def test_open_sheets_recheck_access_when_permissions_change():
    actor = source("static/js/sheets/actors/actor-sheet-events.js")
    item = source("static/js/sheets/items/item-sheet-events.js")

    assert '"actor.updated"' in actor
    assert "if (ok === false)" in actor
    assert '"item.updated"' in item
    assert '"handout.access_changed"' in item
    assert "if (ok === false" in item
