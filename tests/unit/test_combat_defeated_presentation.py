from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "static/js/combat/combat-panel.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/css/game.css").read_text(encoding="utf-8")


def test_turn_order_places_death_skull_over_defeated_portrait() -> None:
    assert "if (combatant.defeated)" in PANEL
    assert 'defeated.src = "/static/icons/base/death-skull.png"' in PANEL
    assert 'defeated.className = "gw-combat-combatant__defeated-icon"' in PANEL
    assert ".gw-combat-combatant__portrait .gw-combat-combatant__defeated-icon" in CSS

