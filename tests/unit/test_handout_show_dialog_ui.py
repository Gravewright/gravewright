from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_show_to_players_is_native_transient_dialog_not_panel_tab():
    template = (ROOT / "templates/pages/game/modals/targeted_handouts.html").read_text(
        encoding="utf-8"
    )
    assert '<dialog class="handout-show-dialog"' in template
    assert "data-handout-dialog" in template
    assert "game-panel" not in template
    assert "game-modal-window" not in template
    assert "data-modal-id" not in template
    assert "data-panel-room" not in template


def test_show_to_players_uses_all_or_selected_player_controls():
    template = (ROOT / "templates/pages/game/modals/targeted_handouts.html").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "static/js/game/targeted-handouts.js").read_text(encoding="utf-8")
    assert 'name="all_players"' in template
    assert 'name="players"' in template
    assert "dialog.showModal()" in script
    assert "dialog.close()" in script
    assert 'request("/game/handouts/present"' in script
    assert 'request("/game/handouts/grant"' not in script
