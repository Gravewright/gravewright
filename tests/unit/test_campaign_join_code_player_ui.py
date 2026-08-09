from __future__ import annotations

from pathlib import Path

from app.i18n.en import CATALOG as EN_MESSAGES
from app.i18n.pt_br import CATALOG as PT_BR_MESSAGES


ROOT = Path(__file__).resolve().parents[2]


def test_inside_has_manual_and_pending_join_code_flows():
    template = (ROOT / "templates/pages/inside/index.html").read_text(encoding="utf-8")
    assert "data-inside-join-code-form" in template
    assert "data-inside-redeem-pending" in template
    assert "{% if has_pending_join_code %}" in template
    assert 'autocomplete="off"' in template
    assert "/static/js/inside/inside-join-code.js" in template


def test_player_script_normalizes_for_ux_without_browser_storage():
    script = (ROOT / "static/js/inside/inside-join-code.js").read_text(encoding="utf-8")
    assert ".toUpperCase()" in script
    assert "replace(/[\\s-]+/g" in script
    assert "/campaigns/join-code/redeem" in script
    assert "window.location.assign" in script
    assert "const data = new URLSearchParams();" in script
    assert "new FormData" not in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_player_join_code_messages_exist_in_both_locales():
    keys = {
        "inside.join_code.title",
        "inside.join_code.description",
        "inside.join_code.pending",
        "inside.join_code.confirm",
        "inside.join_code.errors.request",
        "campaign.join_code.errors.unavailable",
    }
    assert keys <= EN_MESSAGES.keys()
    assert keys <= PT_BR_MESSAGES.keys()
