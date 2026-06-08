from __future__ import annotations

from app.engine.rolls.roll_presentation_service import RollPresentationService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_user


def _enable_dnd5e() -> None:
    user_id = seed_user(name="Owner", email="owner-roll-presentation@test.com")
    svc = SystemInstallService()
    assert svc.install(package_id="dnd5e", user_id=user_id).success
    assert svc.enable(package_id="dnd5e").success


def test_roll_presentation_uses_system_chat_card_and_toast_mapping(db):
    _enable_dnd5e()
    metadata = {
        "actionId": "roll.initiative",
        "actorId": "actor_1",
        "actorName": "Aria",
        "systemId": "dnd5e",
        "label": "Initiative",
        "intent": "check",
        "source": {"kind": "actor", "actorId": "actor_1"},
        "formula": {
            "base": "1d20 + @sheet.init",
            "final": "1d20 + @sheet.init",
            "resolved": "1d20 + 2",
            "display": "1d20 + 2",
        },
        "rollInput": {},
        "presentation": {"chatCard": "check", "rollToast": "check"},
        "visibility": "public",
    }

    rendered = RollPresentationService().render(
        system_id="dnd5e",
        metadata=metadata,
        actor_name="Aria",
        label="Initiative",
        expression="1d20 + 2",
        groups=[{"notation": "1d20", "results": [15], "subtotal": 15}],
        modifier=2,
        total=17,
    ).as_metadata()

    assert rendered["chatCard"]["id"] == "check"
    assert rendered["chatCard"]["title"] == "Aria"
    assert rendered["chatCard"]["subtitle"] == "Initiative"
    assert {line["label"]: line["value"] for line in rendered["chatCard"]["lines"]} == {
        "Fórmula": "1d20 + 2",
        "Total": "17",
    }
    assert rendered["rollToast"]["id"] == "check"
    assert rendered["rollToast"]["title"] == "Aria"
    assert rendered["rollToast"]["total"] == 17


def test_roll_presentation_falls_back_when_mapping_missing(db):
    rendered = RollPresentationService().render(
        system_id="missing-system",
        metadata={"presentation": {"chatCard": "missing"}},
        actor_name="Aria",
        label="Raw Roll",
        expression="1d20",
        groups=[{"notation": "1d20", "results": [9], "subtotal": 9}],
        modifier=0,
        total=9,
    ).as_metadata()

    assert rendered["chatCard"]["id"] == "default"
    assert rendered["chatCard"]["title"] == "Raw Roll"
    assert rendered["rollToast"]["total"] == 9
