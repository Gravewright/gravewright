from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_onboarding_is_transient_dialog_not_a_panel_tab():
    modal = (ROOT / "templates/pages/game/modals/gm_onboarding.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/game/system-onboarding.js").read_text(encoding="utf-8")
    assert modal.lstrip().startswith('<dialog class="gm-onboarding-dialog"')
    assert "game-panel" not in modal
    assert "data-panel-room" not in modal
    assert "localStorage" not in script
    assert "/game/onboarding/preference" in script


def test_onboarding_dialog_remains_clickable_inside_pointerless_modal_layer():
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    dialog_rule = css.split(".gm-onboarding-dialog {", 1)[1].split("}", 1)[0]
    assert "pointer-events: auto" in dialog_rule
    assert 'game.css?v={{ asset_version }}-' in template
