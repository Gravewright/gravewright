from __future__ import annotations

import json
import re

from litestar.testing import TestClient

from tests.conftest import (
    TEST_SESSION_CONFIG,
    login,
    seed_campaign,
    seed_system,
    seed_user,
)


def _client_context(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="gravewright-game-context">(.*?)</script>',
        html,
        re.S,
    )
    assert match, "game client context script not found"
    return json.loads(match.group(1))


def test_game_emits_per_package_nonce_matching_context(db):
    """Each package <script> carries data-gw-package/data-gw-nonce and the nonce
    matches the packageNonces map shipped to the SDK runtime."""
    from main import app

    gm = seed_user(name="GM", email="nonce-gm@test.com")
    campaign = seed_system_campaign(gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        resp = client.get(f"/game?room={campaign}")

    assert resp.status_code == 200
    context = _client_context(resp.text)
    nonces = context["packageNonces"]
    # dnd5e is a scripted ruleset, so it must appear with a non-empty nonce.
    assert nonces.get("dnd5e")

    # The rendered <script> tag for dnd5e carries the very same nonce.
    tag = re.search(
        r'<script[^>]*data-gw-package="dnd5e"[^>]*data-gw-nonce="([^"]+)"[^>]*>',
        resp.text,
    )
    assert tag, "dnd5e package script tag with nonce not found"
    assert tag.group(1) == nonces["dnd5e"]


def seed_system_campaign(gm: str) -> str:
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")
    return campaign
