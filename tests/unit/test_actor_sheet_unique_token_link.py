from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_actor_sheet_uses_the_only_matching_token_in_the_active_scene():
    script = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")

    assert "uniqueActiveSceneTokenForActor(actorId)" in script
    assert "matches.length === 1 ? matches[0] : null" in script
    assert "await ensureTokenSheetModal(tokenId)" in script
    assert "await ensureActorSheetModal(actorId)" in script
