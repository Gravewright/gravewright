from __future__ import annotations

from pathlib import Path

from litestar.testing import TestClient

from app.i18n.en import CATALOG as EN_MESSAGES
from app.i18n.pt_br import CATALOG as PT_BR_MESSAGES
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


ROOT = Path(__file__).resolve().parents[2]


def test_gm_join_code_partial_has_accessible_controls_and_safe_states():
    template = (ROOT / "templates/pages/game/modals/join_code.html").read_text(encoding="utf-8")
    assert "data-join-code-panel" in template
    assert "data-join-code-copy" in template
    assert "data-join-code-revoke" in template
    assert 'aria-live="polite"' in template
    assert "readonly data-join-code-value" in template
    assert "code_hash" not in template


def test_gm_join_code_panel_is_permission_gated_and_scripted():
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    include = '{% include "pages/game/modals/join_code.html" %}'
    include_at = template.index(include)
    assert (
        template.rfind("{% if room.can_invite and campaign_join_code_enabled %}", 0, include_at)
        != -1
    )
    assert 'data-modal-open="join-code-{{ room.id }}"' in template
    assert "/static/js/ui/join-code.js" in template


def test_join_code_javascript_covers_status_copy_confirmations_and_network_errors():
    script = (ROOT / "static/js/ui/join-code.js").read_text(encoding="utf-8")
    assert "/campaigns/join-code/status" in script
    assert "/campaigns/join-code/generate" in script
    assert "/campaigns/join-code/revoke" in script
    assert "navigator.clipboard.writeText" in script
    # Rotate and revoke both still require an explicit confirmation; it is the
    # project dialog now instead of the browser's blocking prompt.
    assert "dialog.confirm(panel.dataset.confirmRotate)" in script
    assert "dialog.confirm(panel.dataset.confirmRevoke" in script
    assert "window.confirm" not in script
    assert '"http.errors.network"' in script
    assert "new URLSearchParams(formData)" in script
    assert "const data = new URLSearchParams();" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_join_code_messages_exist_in_both_locales():
    keys = {
        "game.join_code.title",
        "game.join_code.one_time_warning",
        "game.join_code.confirm_rotate",
        "game.join_code.confirm_revoke",
        "game.join_code.state.active",
        "game.join_code.state.expired",
        "game.join_code.state.revoked",
        "game.join_code.errors.request",
        "campaign.join_code.errors.permission_denied",
    }
    assert keys <= EN_MESSAGES.keys()
    assert keys <= PT_BR_MESSAGES.keys()


def test_gm_game_page_renders_join_code_panel(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.get("/game")
    assert response.status_code == 200, response.text
    assert f'data-modal-id="join-code-{campaign_id}"' in response.text
    assert f'data-modal-open="join-code-{campaign_id}"' in response.text
