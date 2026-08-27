from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_roll_actions_are_constrained_and_do_not_expose_chat_dom() -> None:
    rolls = (ROOT / "static/js/chat/chat-roll-cards.js").read_text(encoding="utf-8")
    sdk = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")

    assert "function registerRollAction(systemId, definition, handler)" in rolls
    assert "definition.intents" in rolls
    assert "definition.actionIds" in rolls
    assert "definition.excludeActionIds" in rolls
    assert "handler(Object.freeze(structuredClone(payload)))" in rolls
    assert "element }" not in rolls
    assert 'requireCap("rolls.actions.register")' in sdk
    assert "chat.register" not in sdk


def test_reroll_api_accepts_only_the_persisted_message_identity() -> None:
    sdk = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    assert "reroll(messageId)" in sdk
    assert 'requireCap("rolls.reroll")' in sdk
    assert 'message_id: String(messageId || "")' in sdk
