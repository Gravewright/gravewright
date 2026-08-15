from __future__ import annotations

from pathlib import Path

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


ROOT = Path(__file__).resolve().parents[2]


def test_command_palette_has_accessible_dialog_and_keyboard_contract():
    template = (ROOT / "templates/pages/game/modals/command_palette.html").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "static/js/ui/command-palette.js").read_text(encoding="utf-8")
    assert 'role="dialog"' in template
    assert 'aria-modal="true"' in template
    assert 'role="listbox"' in template
    assert 'aria-live="polite"' in template
    assert 'event.key.toLowerCase() === "k"' in script
    assert 'event.key === "Escape"' in script
    assert 'event.key === "ArrowDown"' in script
    assert 'event.key === "ArrowUp"' in script
    assert 'event.key === "Enter"' in script
    assert 'event.key === "Tab"' in script
    assert "setTimeout(search, 180)" in script


def test_command_palette_only_contains_safe_open_actions():
    script = (ROOT / "static/js/ui/command-palette.js").read_text(encoding="utf-8")
    assert "vtt:open-actor-sheet" in script
    assert "vtt:open-item-sheet" in script
    assert "vtt:open-journal" in script
    assert "delete" not in script.lower()
    assert "destroy" not in script.lower()


def test_game_page_renders_palette_and_shortcut(db):
    from main import app

    gm_id = seed_user(name="GM")
    seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.get("/game")
    assert response.status_code == 200
    assert "data-command-palette" in response.text
    assert "data-command-palette-open" in response.text
    assert "Control+K Meta+K" in response.text


def test_search_button_is_immediately_before_settings_in_the_dock():
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    dock = template.split('<nav class="game-dock"', 1)[1]
    search = dock.index("data-command-palette-open")
    settings = dock.index('data-panel-toggle="panel-settings-{{ room.id }}"')

    assert search < settings
    assert "data-panel-toggle=" not in dock[search:settings]
